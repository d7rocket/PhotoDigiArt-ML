// PBF Density Constraint: compute density rho_i, constraint C_i, and lambda_i
//
// Uses poly6 kernel for density estimation, spiky kernel gradient for
// constraint gradient. Searches 3x3x3 neighbor cells via spatial hash.

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

@group(0) @binding(0) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(1) var<storage, read> cell_counts: array<u32>;
@group(0) @binding(2) var<storage, read> cell_offsets: array<u32>;
@group(0) @binding(3) var<storage, read> sorted_indices: array<u32>;
@group(0) @binding(4) var<storage, read_write> lambda_out: array<f32>;
@group(0) @binding(5) var<uniform> params: SimParams;

fn pos_to_cell(pos: vec3<f32>, cs: f32) -> vec3<i32> {
    return vec3<i32>(floor((pos + vec3<f32>(64.0)) / cs));
}

fn cell_to_hash(cell: vec3<i32>) -> u32 {
    let cx = u32(clamp(cell.x, 0i, i32(GRID_SIZE) - 1i));
    let cy = u32(clamp(cell.y, 0i, i32(GRID_SIZE) - 1i));
    let cz = u32(clamp(cell.z, 0i, i32(GRID_SIZE) - 1i));
    return cx + cy * GRID_SIZE + cz * GRID_SIZE * GRID_SIZE;
}

// Poly6 kernel: W(r, h) = (315 / (64 * pi * h^9)) * (h^2 - r^2)^3
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

// Spiky kernel gradient magnitude: |grad W| = (45 / (pi * h^6)) * (h - r)^2
// Returns the scalar factor; multiply by direction to get gradient vector.
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
fn compute_density(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let n = u32(params.particle_count);
    if (idx >= n) {
        return;
    }

    let h = params.kernel_radius;
    let pos_i = predicted_positions[idx].xyz;
    let cell_i = pos_to_cell(pos_i, params.cell_size);

    // Accumulate density using poly6 kernel
    var rho_i: f32 = 0.0;
    // Sum of squared constraint gradients for denominator
    var sum_grad_sq: f32 = 0.0;
    var grad_i = vec3<f32>(0.0);  // gradient w.r.t. particle i

    // Search 3x3x3 neighbor cells
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let neighbor_cell = cell_i + vec3<i32>(dx, dy, dz);

                // Bounds check
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

                    let pos_j = predicted_positions[j].xyz;
                    let diff = pos_i - pos_j;
                    let r_sq = dot(diff, diff);

                    // Density accumulation (poly6)
                    rho_i = rho_i + poly6(r_sq, h);

                    // Gradient accumulation (spiky) for constraint denominator
                    let r = sqrt(r_sq);
                    if (r > 0.0001 && r < h) {
                        let dir = diff / r;
                        let grad_factor = spiky_grad_factor(r, h);
                        let grad_wj = dir * grad_factor;

                        if (j != idx) {
                            // Gradient w.r.t. neighbor j: (1/rho_0) * grad_W
                            let scaled_grad = grad_wj / params.rest_density;
                            sum_grad_sq = sum_grad_sq + dot(scaled_grad, scaled_grad);
                        }
                        // Accumulate gradient w.r.t. particle i
                        grad_i = grad_i - grad_wj;
                    }
                }
            }
        }
    }

    // Add gradient w.r.t. particle i to denominator
    let scaled_grad_i = grad_i / params.rest_density;
    sum_grad_sq = sum_grad_sq + dot(scaled_grad_i, scaled_grad_i);

    // Constraint: C_i = (rho_i / rest_density) - 1
    let c_i = (rho_i / params.rest_density) - 1.0;

    // Lambda: lambda_i = -C_i / (sum_grad_sq + epsilon)
    var lambda_i = -c_i / (sum_grad_sq + params.epsilon_pbf);

    // NaN/Inf guard (WGSL has no isnan/isinf -- use arithmetic checks)
    if (lambda_i != lambda_i || lambda_i - lambda_i != 0.0) {
        lambda_i = 0.0;
    }

    lambda_out[idx] = lambda_i;
}
