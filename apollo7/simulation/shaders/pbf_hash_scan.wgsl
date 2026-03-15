// PBF Hash Scan: Blelloch-style tree-reduction parallel prefix sum
//
// Two entry points for up-sweep (reduce) and down-sweep (scatter).
// Workgroup size 256 processes 512 elements per workgroup.
// For 2M cells, multi-level dispatch is handled by PBFSolver Python class.

const WG_SIZE: u32 = 256u;
const ELEMENTS_PER_WG: u32 = 512u;

@group(0) @binding(0) var<storage, read_write> data: array<u32>;

var<workgroup> shared_data: array<u32, 512>;

@compute @workgroup_size(256)
fn prefix_sum_up(@builtin(global_invocation_id) gid: vec3<u32>,
                 @builtin(local_invocation_id) lid: vec3<u32>,
                 @builtin(workgroup_id) wgid: vec3<u32>) {
    let local_id = lid.x;
    let base = wgid.x * ELEMENTS_PER_WG;
    let n = arrayLength(&data);

    // Load two elements per thread into shared memory
    let idx0 = base + local_id;
    let idx1 = base + local_id + WG_SIZE;

    if (idx0 < n) {
        shared_data[local_id] = data[idx0];
    } else {
        shared_data[local_id] = 0u;
    }
    if (idx1 < n) {
        shared_data[local_id + WG_SIZE] = data[idx1];
    } else {
        shared_data[local_id + WG_SIZE] = 0u;
    }

    // Up-sweep (reduce) phase
    var offset = 1u;
    var d = ELEMENTS_PER_WG >> 1u;
    while (d > 0u) {
        workgroupBarrier();
        if (local_id < d) {
            let ai = offset * (2u * local_id + 1u) - 1u;
            let bi = offset * (2u * local_id + 2u) - 1u;
            shared_data[bi] = shared_data[bi] + shared_data[ai];
        }
        offset = offset << 1u;
        d = d >> 1u;
    }

    // Store block sum and clear last element for down-sweep
    workgroupBarrier();
    if (local_id == 0u) {
        // The last element holds the total sum for this block
        // We leave it for the block-sum collection pass
        shared_data[ELEMENTS_PER_WG - 1u] = 0u;
    }

    // Down-sweep phase
    d = 1u;
    offset = ELEMENTS_PER_WG >> 1u;
    while (d < ELEMENTS_PER_WG) {
        workgroupBarrier();
        if (local_id < d) {
            let ai = offset * (2u * local_id + 1u) - 1u;
            let bi = offset * (2u * local_id + 2u) - 1u;
            let tmp = shared_data[ai];
            shared_data[ai] = shared_data[bi];
            shared_data[bi] = shared_data[bi] + tmp;
        }
        d = d << 1u;
        offset = offset >> 1u;
    }

    workgroupBarrier();

    // Write results back
    if (idx0 < n) {
        data[idx0] = shared_data[local_id];
    }
    if (idx1 < n) {
        data[idx1] = shared_data[local_id + WG_SIZE];
    }
}

@compute @workgroup_size(256)
fn prefix_sum_down(@builtin(global_invocation_id) gid: vec3<u32>,
                   @builtin(local_invocation_id) lid: vec3<u32>,
                   @builtin(workgroup_id) wgid: vec3<u32>) {
    // This entry point adds block sums back to produce the final prefix sum.
    // Each thread adds the block sum for its workgroup to each element.
    // The block_sums array is passed as a second section of the data buffer,
    // or as a separate dispatch after the block sums are computed.
    //
    // For the PBFSolver, this is handled via a separate add-block-sums shader
    // dispatch. This entry point is a placeholder for the down-sweep fixup.
    let local_id = lid.x;
    let base = wgid.x * ELEMENTS_PER_WG;
    let n = arrayLength(&data);

    let idx0 = base + local_id;
    let idx1 = base + local_id + WG_SIZE;

    // No-op for single-level scan -- the up-sweep already produced
    // the within-block prefix sum. Multi-level fixup is handled by
    // PBFSolver._dispatch_prefix_sum() in Python.
    _ = idx0;
    _ = idx1;
}
