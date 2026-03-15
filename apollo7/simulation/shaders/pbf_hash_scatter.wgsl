// PBF Hash Scatter: place particles in sorted order by cell hash
//
// Uses atomicAdd on cell_offsets to get unique write positions,
// then writes particle indices into sorted_indices array.

struct SimParams {
    noise_frequency: f32,
    noise_amplitude: f32,
    noise_octaves: f32,
    turbulence_scale: f32,
    home_strength: f32,
    breathing_rate: f32,
    breathing_amplitude: f32,
    breathing_mod: f32,
    kernel_radius: f32,
    rest_density: f32,
    epsilon_pbf: f32,
    solver_iterations: f32,
    artificial_pressure_k: f32,
    artificial_pressure_n: f32,
    delta_q: f32,
    xsph_c: f32,
    vorticity_epsilon: f32,
    max_force: f32,
    max_velocity: f32,
    dt: f32,
    gravity_x: f32,
    gravity_y: f32,
    gravity_z: f32,
    damping: f32,
    wind_x: f32,
    wind_y: f32,
    wind_z: f32,
    speed: f32,
    time: f32,
    cell_size: f32,
    particle_count: f32,
    _pad: f32,
};

const GRID_SIZE: u32 = 128u;
const GRID_TOTAL: u32 = 2097152u;  // 128^3

@group(0) @binding(0) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read_write> cell_offsets: array<atomic<u32>>;
@group(0) @binding(2) var<storage, read_write> sorted_indices: array<u32>;
@group(0) @binding(3) var<uniform> params: SimParams;

fn pos_to_hash(pos: vec3<f32>, cs: f32) -> u32 {
    let cell = vec3<i32>(floor((pos + vec3<f32>(64.0)) / cs));
    let cx = clamp(cell.x, 0i, i32(GRID_SIZE) - 1i);
    let cy = clamp(cell.y, 0i, i32(GRID_SIZE) - 1i);
    let cz = clamp(cell.z, 0i, i32(GRID_SIZE) - 1i);
    return u32(cx) + u32(cy) * GRID_SIZE + u32(cz) * GRID_SIZE * GRID_SIZE;
}

@compute @workgroup_size(256)
fn hash_scatter(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let n = u32(params.particle_count);
    if (idx >= n) {
        return;
    }

    let pos = predicted_positions[idx].xyz;
    let hash = pos_to_hash(pos, params.cell_size);
    let offset = atomicAdd(&cell_offsets[hash], 1u);
    sorted_indices[offset] = idx;
}
