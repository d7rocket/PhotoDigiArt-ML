"""PBF (Position Based Fluids) solver orchestration.

Builds and dispatches the full PBF compute pipeline per frame:
  predict -> hash (count/scan/scatter) -> density/correct loop -> finalize

Uses GPU spatial hashing via counting sort with atomics and a
Blelloch-style parallel prefix sum. Constraint solving iterates
density + correction passes for the configured solver_iterations.

Designed for 1-5M particles with chunked dispatch for AMD TDR prevention.
"""

from __future__ import annotations

import logging
import struct

import numpy as np

from apollo7.simulation.buffers import GRID_TOTAL_CELLS, ParticleBuffer
from apollo7.simulation.parameters import SimulationParams
from apollo7.simulation.shaders import build_combined_shader, load_shader

logger = logging.getLogger(__name__)

# Maximum particles per compute dispatch (AMD TDR prevention)
_CHUNK_SIZE = 256 * 1024  # 256K particles
_WORKGROUP_SIZE = 256

# Prefix sum: elements processed per workgroup (2 elements per thread)
_SCAN_ELEMENTS_PER_WG = 512


class PBFSolver:
    """Orchestrates the PBF compute pipeline for particle simulation.

    The solver manages all GPU compute pipelines and bind groups for
    the Position Based Fluids algorithm. Each call to step() executes
    the full pipeline: predict, spatial hash rebuild, iterative density
    constraint solving, and finalization.
    """

    def __init__(self, device, particle_buffer: ParticleBuffer):
        """Build all compute pipelines and bind group layouts.

        Args:
            device: wgpu.GPUDevice for pipeline and buffer creation.
            particle_buffer: ParticleBuffer with all required GPU buffers.
        """
        import wgpu

        self._device = device
        self._pb = particle_buffer
        self._wgpu = wgpu

        # Zero buffer for clearing cell counts (8MB for 2M cells * 4 bytes)
        self._zero_bytes = bytes(GRID_TOTAL_CELLS * 4)

        # Block sums buffer for multi-level prefix sum
        n_blocks_l1 = (GRID_TOTAL_CELLS + _SCAN_ELEMENTS_PER_WG - 1) // _SCAN_ELEMENTS_PER_WG
        self._n_blocks_l1 = n_blocks_l1
        self._block_sums_buf = device.create_buffer(
            size=max(n_blocks_l1 * 4, 4),
            usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST | wgpu.BufferUsage.COPY_SRC,
        )
        # Level 2 block sums (for n_blocks_l1 elements)
        n_blocks_l2 = (n_blocks_l1 + _SCAN_ELEMENTS_PER_WG - 1) // _SCAN_ELEMENTS_PER_WG
        self._n_blocks_l2 = n_blocks_l2
        self._block_sums_l2_buf = device.create_buffer(
            size=max(n_blocks_l2 * 4, 4),
            usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_DST | wgpu.BufferUsage.COPY_SRC,
        )

        # Build all pipelines
        self._build_predict_pipeline()
        self._build_hash_count_pipeline()
        self._build_hash_scan_pipeline()
        self._build_hash_scatter_pipeline()
        self._build_density_pipeline()
        self._build_correct_pipeline()
        self._build_finalize_pipeline()
        self._build_add_block_sums_pipeline()

        # Cached bind groups per buffer orientation
        self._bind_groups = {"a": {}, "b": {}}
        self._rebuild_all_bind_groups()

        logger.info("PBFSolver initialized with all compute pipelines")

    def step(self, params: SimulationParams) -> None:
        """Execute one full PBF frame.

        Pipeline order:
        1. Update params uniform buffer
        2. Predict positions (external forces + Euler step)
        3. Clear cell counts
        4. Hash count (atomicAdd per cell)
        5. Prefix sum on cell counts -> cell offsets
        6. Hash scatter (sorted indices)
        7. Constraint loop (density + correction) x solver_iterations
        8. Finalize (velocity from displacement + clamping)
        9. Swap particle buffers

        Args:
            params: Current simulation parameters.
        """
        pb = self._pb
        n = pb.particle_count
        if n == 0:
            return

        orientation = pb._current_input
        bg = self._bind_groups[orientation]

        # 1. Update params
        pb.update_params(params)

        # 2. Predict pass
        self._dispatch_compute(self._predict_pipeline, bg["predict"], n)

        # 3. Clear cell counts buffer
        self._device.queue.write_buffer(
            pb.cell_counts_buffer, 0, self._zero_bytes
        )

        # 4. Hash count
        self._dispatch_compute(self._hash_count_pipeline, bg["hash_count"], n)

        # 5. Prefix sum: cell_counts -> cell_offsets
        self._dispatch_prefix_sum()

        # 6. Hash scatter
        self._dispatch_compute(self._hash_scatter_pipeline, bg["hash_scatter"], n)

        # 7. Constraint loop
        iterations = max(1, int(params.solver_iterations))
        for _ in range(iterations):
            self._dispatch_compute(self._density_pipeline, bg["density"], n)
            self._dispatch_compute(self._correct_pipeline, bg["correct"], n)

        # 8. Finalize
        self._dispatch_compute(self._finalize_pipeline, bg["finalize"], n)

        # 9. Swap buffers
        pb.swap()

        # Rebuild bind groups for new orientation
        new_orientation = pb._current_input
        if new_orientation != orientation:
            self._rebuild_all_bind_groups()

    def _dispatch_compute(self, pipeline, bind_group, total_particles: int) -> None:
        """Dispatch a compute shader with chunked AMD TDR prevention.

        Each chunk gets its own command encoder submission for
        proper GPU synchronization.

        Args:
            pipeline: Compute pipeline to dispatch.
            bind_group: Bind group for the pipeline.
            total_particles: Total particles to process.
        """
        for offset in range(0, total_particles, _CHUNK_SIZE):
            count = min(_CHUNK_SIZE, total_particles - offset)
            workgroups = (count + _WORKGROUP_SIZE - 1) // _WORKGROUP_SIZE

            encoder = self._device.create_command_encoder()
            compute_pass = encoder.begin_compute_pass()
            compute_pass.set_pipeline(pipeline)
            compute_pass.set_bind_group(0, bind_group)
            compute_pass.dispatch_workgroups(workgroups)
            compute_pass.end()
            self._device.queue.submit([encoder.finish()])

    def _dispatch_prefix_sum(self) -> None:
        """Multi-level parallel prefix sum on cell_counts -> cell_offsets.

        Level 1: Scan cell_offsets in blocks of 512, extract block sums.
        Level 2: Scan block sums.
        Fixup: Add scanned block sums back to each block.

        For 2M cells: L1 = 4096 workgroups, L2 = 8 workgroups.
        """
        pb = self._pb
        wgpu = self._wgpu
        n_cells = GRID_TOTAL_CELLS

        # Copy cell_counts to cell_offsets (prefix sum operates in-place)
        encoder = self._device.create_command_encoder()
        encoder.copy_buffer_to_buffer(
            pb.cell_counts_buffer, 0,
            pb.cell_offsets_buffer, 0,
            n_cells * 4,
        )
        self._device.queue.submit([encoder.finish()])

        # Level 1: within-block prefix sum on cell_offsets
        # Each workgroup processes 512 elements
        n_wg_l1 = (n_cells + _SCAN_ELEMENTS_PER_WG - 1) // _SCAN_ELEMENTS_PER_WG

        encoder = self._device.create_command_encoder()
        compute_pass = encoder.begin_compute_pass()
        compute_pass.set_pipeline(self._scan_pipeline)
        compute_pass.set_bind_group(0, self._scan_bg_offsets)
        compute_pass.dispatch_workgroups(n_wg_l1)
        compute_pass.end()
        self._device.queue.submit([encoder.finish()])

        # Extract block sums: last element of each block before it was zeroed
        # Since Blelloch scan zeros the last element, we need to read original
        # block totals. We re-read from cell_counts and compute cumulative.
        # Alternative: use the cell_counts to compute block sums directly.
        self._compute_block_sums_from_counts(n_wg_l1)

        if n_wg_l1 > 1:
            # Level 2: prefix sum on block sums
            n_wg_l2 = (n_wg_l1 + _SCAN_ELEMENTS_PER_WG - 1) // _SCAN_ELEMENTS_PER_WG

            encoder = self._device.create_command_encoder()
            compute_pass = encoder.begin_compute_pass()
            compute_pass.set_pipeline(self._scan_pipeline)
            compute_pass.set_bind_group(0, self._scan_bg_blocks)
            compute_pass.dispatch_workgroups(n_wg_l2)
            compute_pass.end()
            self._device.queue.submit([encoder.finish()])

            # Fixup: add block sums to each element in cell_offsets
            encoder = self._device.create_command_encoder()
            compute_pass = encoder.begin_compute_pass()
            compute_pass.set_pipeline(self._add_block_sums_pipeline)
            compute_pass.set_bind_group(0, self._add_block_sums_bg)
            # One workgroup per block in level 1
            compute_pass.dispatch_workgroups(n_wg_l1)
            compute_pass.end()
            self._device.queue.submit([encoder.finish()])

    def _compute_block_sums_from_counts(self, n_blocks: int) -> None:
        """Compute block sums from cell_counts for prefix sum fixup.

        Each block sum is the total count of particles in that block's
        range of cells. We compute this on CPU from cell_counts since
        the scan has already modified cell_offsets.

        Args:
            n_blocks: Number of blocks in level 1.
        """
        # Read cell_counts from GPU
        counts_raw = self._device.queue.read_buffer(
            self._pb.cell_counts_buffer, 0, GRID_TOTAL_CELLS * 4
        )
        counts = np.frombuffer(counts_raw, dtype=np.uint32)

        # Compute block sums
        block_sums = np.zeros(n_blocks, dtype=np.uint32)
        for b in range(n_blocks):
            start = b * _SCAN_ELEMENTS_PER_WG
            end = min(start + _SCAN_ELEMENTS_PER_WG, GRID_TOTAL_CELLS)
            block_sums[b] = np.sum(counts[start:end])

        # Upload block sums
        self._device.queue.write_buffer(
            self._block_sums_buf, 0, block_sums.tobytes()
        )

    # -------------------------------------------------------------------------
    # Pipeline builders
    # -------------------------------------------------------------------------

    def _build_predict_pipeline(self) -> None:
        """Build predict pass compute pipeline.

        Uses combined shader (noise + pbf_predict) so curl_noise_3d
        is available in the predict entry point.
        """
        wgpu = self._wgpu
        shader = self._device.create_shader_module(
            code=build_combined_shader("noise", "pbf_predict")
        )

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._predict_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "pbf_predict"},
        )
        self._predict_bgl = bgl

    def _build_hash_count_pipeline(self) -> None:
        """Build hash count compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_hash_count"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._hash_count_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "hash_count"},
        )
        self._hash_count_bgl = bgl

    def _build_hash_scan_pipeline(self) -> None:
        """Build prefix sum compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_hash_scan"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._scan_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "prefix_sum_up"},
        )
        self._scan_bgl = bgl

        # Bind groups for scanning different buffers
        self._scan_bg_offsets = self._device.create_bind_group(
            layout=bgl,
            entries=[{"binding": 0, "resource": {
                "buffer": self._pb.cell_offsets_buffer,
                "offset": 0, "size": self._pb.cell_offsets_buffer.size,
            }}],
        )
        self._scan_bg_blocks = self._device.create_bind_group(
            layout=bgl,
            entries=[{"binding": 0, "resource": {
                "buffer": self._block_sums_buf,
                "offset": 0, "size": self._block_sums_buf.size,
            }}],
        )

    def _build_hash_scatter_pipeline(self) -> None:
        """Build hash scatter compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_hash_scatter"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._hash_scatter_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "hash_scatter"},
        )
        self._hash_scatter_bgl = bgl

    def _build_density_pipeline(self) -> None:
        """Build density constraint compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_density"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 4, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 5, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._density_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "compute_density"},
        )
        self._density_bgl = bgl

    def _build_correct_pipeline(self) -> None:
        """Build position correction compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_correct"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 4, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 5, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 6, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._correct_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "compute_correction"},
        )
        self._correct_bgl = bgl

    def _build_finalize_pipeline(self) -> None:
        """Build finalize compute pipeline."""
        wgpu = self._wgpu
        shader = self._device.create_shader_module(code=load_shader("pbf_finalize"))

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
            {"binding": 2, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 3, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.uniform}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._finalize_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "pbf_finalize"},
        )
        self._finalize_bgl = bgl

    def _build_add_block_sums_pipeline(self) -> None:
        """Build the add-block-sums fixup compute pipeline.

        This shader adds scanned block sums back to each element in the
        cell_offsets buffer to complete the multi-level prefix sum.
        """
        wgpu = self._wgpu

        # Inline WGSL for the fixup shader
        shader_src = """
const ELEMENTS_PER_WG: u32 = 512u;
const WG_SIZE: u32 = 256u;

@group(0) @binding(0) var<storage, read_write> data: array<u32>;
@group(0) @binding(1) var<storage, read> block_sums: array<u32>;

@compute @workgroup_size(256)
fn add_block_sums(@builtin(global_invocation_id) gid: vec3<u32>,
                  @builtin(local_invocation_id) lid: vec3<u32>,
                  @builtin(workgroup_id) wgid: vec3<u32>) {
    let block_id = wgid.x;
    let local_id = lid.x;
    let n = arrayLength(&data);

    // Skip first block (no offset to add)
    if (block_id == 0u) {
        return;
    }

    let block_sum = block_sums[block_id];
    let base = block_id * ELEMENTS_PER_WG;

    let idx0 = base + local_id;
    let idx1 = base + local_id + WG_SIZE;

    if (idx0 < n) {
        data[idx0] = data[idx0] + block_sum;
    }
    if (idx1 < n) {
        data[idx1] = data[idx1] + block_sum;
    }
}
"""
        shader = self._device.create_shader_module(code=shader_src)

        bgl = self._device.create_bind_group_layout(entries=[
            {"binding": 0, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.storage}},
            {"binding": 1, "visibility": wgpu.ShaderStage.COMPUTE,
             "buffer": {"type": wgpu.BufferBindingType.read_only_storage}},
        ])
        layout = self._device.create_pipeline_layout(bind_group_layouts=[bgl])
        self._add_block_sums_pipeline = self._device.create_compute_pipeline(
            layout=layout,
            compute={"module": shader, "entry_point": "add_block_sums"},
        )
        self._add_block_sums_bgl = bgl

        # Bind group: data=cell_offsets, block_sums=block_sums_buf
        self._add_block_sums_bg = self._device.create_bind_group(
            layout=bgl,
            entries=[
                {"binding": 0, "resource": {
                    "buffer": self._pb.cell_offsets_buffer,
                    "offset": 0, "size": self._pb.cell_offsets_buffer.size,
                }},
                {"binding": 1, "resource": {
                    "buffer": self._block_sums_buf,
                    "offset": 0, "size": self._block_sums_buf.size,
                }},
            ],
        )

    # -------------------------------------------------------------------------
    # Bind group management
    # -------------------------------------------------------------------------

    def _rebuild_all_bind_groups(self) -> None:
        """Rebuild bind groups for both buffer orientations."""
        for orient in ("a", "b"):
            self._bind_groups[orient] = self._create_bind_groups(orient)

    def _create_bind_groups(self, orientation: str) -> dict:
        """Create bind groups for the given buffer orientation.

        Args:
            orientation: "a" or "b" indicating which buffer is input.

        Returns:
            Dict mapping pipeline name to bind group.
        """
        pb = self._pb
        if orientation == "a":
            input_buf = pb._buf_a
            output_buf = pb._buf_b
        else:
            input_buf = pb._buf_b
            output_buf = pb._buf_a

        def _res(buf):
            return {"buffer": buf, "offset": 0, "size": buf.size}

        groups = {}

        # Predict: particles_in, predicted_out, home_positions, params
        groups["predict"] = self._device.create_bind_group(
            layout=self._predict_bgl,
            entries=[
                {"binding": 0, "resource": _res(input_buf)},
                {"binding": 1, "resource": _res(pb.predicted_buffer)},
                {"binding": 2, "resource": _res(pb.home_positions_buffer)},
                {"binding": 3, "resource": _res(pb.params_buffer)},
            ],
        )

        # Hash count: predicted, cell_counts, params
        groups["hash_count"] = self._device.create_bind_group(
            layout=self._hash_count_bgl,
            entries=[
                {"binding": 0, "resource": _res(pb.predicted_buffer)},
                {"binding": 1, "resource": _res(pb.cell_counts_buffer)},
                {"binding": 2, "resource": _res(pb.params_buffer)},
            ],
        )

        # Hash scatter: predicted, cell_offsets, sorted_indices, params
        groups["hash_scatter"] = self._device.create_bind_group(
            layout=self._hash_scatter_bgl,
            entries=[
                {"binding": 0, "resource": _res(pb.predicted_buffer)},
                {"binding": 1, "resource": _res(pb.cell_offsets_buffer)},
                {"binding": 2, "resource": _res(pb.sorted_indices_buffer)},
                {"binding": 3, "resource": _res(pb.params_buffer)},
            ],
        )

        # Density: predicted, cell_counts, cell_offsets, sorted_indices, lambda, params
        groups["density"] = self._device.create_bind_group(
            layout=self._density_bgl,
            entries=[
                {"binding": 0, "resource": _res(pb.predicted_buffer)},
                {"binding": 1, "resource": _res(pb.cell_counts_buffer)},
                {"binding": 2, "resource": _res(pb.cell_offsets_buffer)},
                {"binding": 3, "resource": _res(pb.sorted_indices_buffer)},
                {"binding": 4, "resource": _res(pb.lambda_buffer)},
                {"binding": 5, "resource": _res(pb.params_buffer)},
            ],
        )

        # Correct: predicted(rw), lambda, cell_counts, cell_offsets, sorted_indices, delta_p, params
        groups["correct"] = self._device.create_bind_group(
            layout=self._correct_bgl,
            entries=[
                {"binding": 0, "resource": _res(pb.predicted_buffer)},
                {"binding": 1, "resource": _res(pb.lambda_buffer)},
                {"binding": 2, "resource": _res(pb.cell_counts_buffer)},
                {"binding": 3, "resource": _res(pb.cell_offsets_buffer)},
                {"binding": 4, "resource": _res(pb.sorted_indices_buffer)},
                {"binding": 5, "resource": _res(pb.delta_p_buffer)},
                {"binding": 6, "resource": _res(pb.params_buffer)},
            ],
        )

        # Finalize: particles_in, predicted, particles_out, params
        groups["finalize"] = self._device.create_bind_group(
            layout=self._finalize_bgl,
            entries=[
                {"binding": 0, "resource": _res(input_buf)},
                {"binding": 1, "resource": _res(pb.predicted_buffer)},
                {"binding": 2, "resource": _res(output_buf)},
                {"binding": 3, "resource": _res(pb.params_buffer)},
            ],
        )

        return groups
