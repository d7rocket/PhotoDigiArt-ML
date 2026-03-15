// PBF Position Correction: compute delta_p with artificial pressure
//
// For each particle, computes position correction from lambda values
// and neighbor interactions. Applies artificial pressure (tensile
// instability fix) and writes corrected positions.

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
const GRID_TOTAL: u32 = 2097152u;
const PI: f32 = 3.14159265359;

@group(0) @binding(0) var<storage, read_write> predicted_positions: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read> lambda_buf: array<f32>;
@group(0) @binding(2) var<storage, read> cell_counts: array<u32>;
@group(0) @binding(3) var<storage, read> cell_offsets: array<u32>;
@group(0) @binding(4) var<storage, read> sorted_indices: array<u32>;
@group(0) @binding(5) var<storage, read_write> delta_p: array<vec4<f32>>;
@group(0) @binding(6) var<uniform> params: SimParams;

fn pos_to_cell(pos: vec3<f32>, cs: f32) -> vec3<i32> {
    return vec3<i32>(floor((pos + vec3<f32>(64.0)) / cs));
}

fn cell_to_hash(cell: vec3<i32>) -> u32 {
    let cx = u32(clamp(cell.x, 0i, i32(GRID_SIZE) - 1i));
    let cy = u32(clamp(cell.y, 0i, i32(GRID_SIZE) - 1i));
    let cz = u32(clamp(cell.z, 0i, i32(GRID_SIZE) - 1i));
    return cx + cy * GRID_SIZE + cz * GRID_SIZE * GRID_SIZE;
}

// Poly6 kernel for artificial pressure reference
fn poly6(r_sq: f32, h: f32) -> f32 {
    let h_sq = h * h;
    if (r_sq >= h_sq) {
        return 0.0;
    }
    let diff = h_sq - r_sq;
    let h9 = h * h * h * h * h * h * h * h * h;
    let coeff = 315.0 / (64.0 * PI * h9);
    return coeff * diff * diff * diff;
}

// Spiky kernel gradient factor
fn spiky_grad_factor(r: f32, h: f32) -> f32 {
    if (r >= h || r < 0.0001) {
        return 0.0;
    }
    let diff = h - r;
    let h6 = h * h * h * h * h * h;
    let coeff = -45.0 / (PI * h6);
    return coeff * diff * diff;
}

@compute @workgroup_size(256)
fn compute_correction(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let n = u32(params.particle_count);
    if (idx >= n) {
        return;
    }

    let h = params.kernel_radius;
    let pos_i = predicted_positions[idx].xyz;
    let cell_i = pos_to_cell(pos_i, params.cell_size);
    let lambda_i = lambda_buf[idx];

    // Precompute W(delta_q * h) for artificial pressure
    let dq = params.delta_q * h;
    let w_dq = poly6(dq * dq, h);

    var dp_i = vec3<f32>(0.0);

    // Search 3x3x3 neighbor cells
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let neighbor_cell = cell_i + vec3<i32>(dx, dy, dz);

                if (neighbor_cell.x < 0 || neighbor_cell.x >= i32(GRID_SIZE) ||
                    neighbor_cell.y < 0 || neighbor_cell.y >= i32(GRID_SIZE) ||
                    neighbor_cell.z < 0 || neighbor_cell.z >= i32(GRID_SIZE)) {
                    continue;
                }

                let cell_hash = cell_to_hash(neighbor_cell);
                let count = cell_counts[cell_hash];
                let offset = cell_offsets[cell_hash];

                for (var k: u32 = 0u; k < count; k = k + 1u) {
                    let j = sorted_indices[offset + k];
                    if (j == idx) {
                        continue;
                    }

                    let pos_j = predicted_positions[j].xyz;
                    let diff = pos_i - pos_j;
                    let r_sq = dot(diff, diff);
                    let r = sqrt(r_sq);

                    if (r >= h || r < 0.0001) {
                        continue;
                    }

                    let lambda_j = lambda_buf[j];

                    // Artificial pressure: s_corr = -k * (W(r) / W(delta_q * h))^n
                    var s_corr: f32 = 0.0;
                    if (w_dq > 0.0001) {
                        let w_ij = poly6(r_sq, h);
                        let ratio = w_ij / w_dq;
                        s_corr = -params.artificial_pressure_k * pow(ratio, params.artificial_pressure_n);
                    }

                    // Gradient (spiky kernel)
                    let dir = diff / r;
                    let grad_factor = spiky_grad_factor(r, h);
                    let grad_w = dir * grad_factor;

                    // Position correction
                    dp_i = dp_i + (lambda_i + lambda_j + s_corr) * grad_w;
                }
            }
        }
    }

    // Scale by 1/rest_density
    dp_i = dp_i / params.rest_density;

    // NaN/Inf guard on delta_p (WGSL has no isnan/isinf)
    if (dp_i.x != dp_i.x || dp_i.y != dp_i.y || dp_i.z != dp_i.z ||
        dp_i.x - dp_i.x != 0.0 || dp_i.y - dp_i.y != 0.0 || dp_i.z - dp_i.z != 0.0) {
        dp_i = vec3<f32>(0.0);
    }

    // Write correction and apply to predicted position
    delta_p[idx] = vec4<f32>(dp_i, 0.0);
    predicted_positions[idx] = vec4<f32>(pos_i + dp_i, 0.0);
}
