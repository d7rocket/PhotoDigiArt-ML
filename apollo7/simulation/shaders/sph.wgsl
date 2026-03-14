// sph.wgsl -- SPH (Smoothed Particle Hydrodynamics) compute shaders.
//
// Three-pass implementation:
// 1. Hash pass: assign particles to spatial hash grid cells
// 2. Density pass: compute density at each particle using poly6 kernel
// 3. Force pass: compute pressure (spiky kernel) + viscosity forces
//
// Uses spatial hashing for O(N*k) neighbor search (k = avg neighbors).

// --------------------------------------------------------------------------
// Struct definitions
// --------------------------------------------------------------------------

struct Particle {
    pos: vec4<f32>,
    vel: vec4<f32>,
};

struct SimParams {
    noise_frequency: f32,
    noise_amplitude: f32,
    noise_octaves: f32,
    turbulence_scale: f32,
    viscosity: f32,
    pressure_strength: f32,
    surface_tension: f32,
    attraction_strength: f32,
    repulsion_strength: f32,
    repulsion_radius: f32,
    smoothing_radius: f32,
    rest_density: f32,
    gas_constant: f32,
    speed: f32,
    dt: f32,
    damping: f32,
    gravity: vec4<f32>,
    wind: vec4<f32>,
    time: f32,
    sph_enabled: f32,
    performance_mode: f32,
    _pad2: f32,
};

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------

const PI: f32 = 3.14159265359;
const GRID_SIZE: u32 = 128u;
const GRID_OFFSET: f32 = 64.0;

// --------------------------------------------------------------------------
// Bindings -- Density pass
// --------------------------------------------------------------------------

@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<uniform> params: SimParams;
@group(0) @binding(2) var<storage, read_write> densities: array<f32>;
@group(0) @binding(3) var<storage, read> cell_counts: array<u32>;
@group(0) @binding(4) var<storage, read> cell_offsets: array<u32>;
@group(0) @binding(5) var<storage, read> sorted_indices: array<u32>;

// Force pass uses separate bind group
@group(0) @binding(6) var<storage, read_write> sph_forces: array<vec4<f32>>;

// --------------------------------------------------------------------------
// Spatial hash helpers
// --------------------------------------------------------------------------

fn sph_pos_to_cell(pos: vec3<f32>, cell_size: f32) -> vec3<i32> {
    return vec3<i32>(floor((pos + vec3<f32>(GRID_OFFSET)) / cell_size));
}

fn sph_cell_to_hash(cell: vec3<i32>) -> u32 {
    let cx = u32(cell.x) % GRID_SIZE;
    let cy = u32(cell.y) % GRID_SIZE;
    let cz = u32(cell.z) % GRID_SIZE;
    return cx + cy * GRID_SIZE + cz * GRID_SIZE * GRID_SIZE;
}

// --------------------------------------------------------------------------
// SPH Kernels
// --------------------------------------------------------------------------

// Poly6 kernel -- used for density estimation
// W_poly6(r, h) = 315 / (64 * pi * h^9) * (h^2 - r^2)^3
fn poly6_kernel(r_sq: f32, h: f32) -> f32 {
    let h_sq = h * h;
    if (r_sq >= h_sq) {
        return 0.0;
    }
    let diff = h_sq - r_sq;
    let coeff = 315.0 / (64.0 * PI * pow(h, 9.0));
    return coeff * diff * diff * diff;
}

// Spiky kernel gradient -- used for pressure force
// grad W_spiky(r, h) = -45 / (pi * h^6) * (h - r)^2 * (r_hat)
fn spiky_kernel_gradient(r: f32, h: f32) -> f32 {
    if (r >= h || r < 0.0001) {
        return 0.0;
    }
    let diff = h - r;
    let coeff = -45.0 / (PI * pow(h, 6.0));
    return coeff * diff * diff;
}

// Viscosity kernel laplacian -- used for viscosity force
// laplacian W_visc(r, h) = 45 / (pi * h^6) * (h - r)
fn viscosity_kernel_laplacian(r: f32, h: f32) -> f32 {
    if (r >= h) {
        return 0.0;
    }
    let coeff = 45.0 / (PI * pow(h, 6.0));
    return coeff * (h - r);
}

// --------------------------------------------------------------------------
// Density computation (pass 1)
// --------------------------------------------------------------------------

@compute @workgroup_size(256)
fn compute_density(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    let count = arrayLength(&particles_in);
    if (idx >= count) {
        return;
    }

    let pos = particles_in[idx].pos.xyz;
    let h = params.smoothing_radius;
    let cell_size = h;
    let my_cell = sph_pos_to_cell(pos, cell_size);

    var density: f32 = 0.0;

    // Self-contribution
    density = density + poly6_kernel(0.0, h);

    // Search 3x3x3 neighborhood
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let neighbor_cell = my_cell + vec3<i32>(dx, dy, dz);

                if (any(neighbor_cell < vec3<i32>(0)) ||
                    any(neighbor_cell >= vec3<i32>(i32(GRID_SIZE)))) {
                    continue;
                }

                let hash = sph_cell_to_hash(neighbor_cell);
                let start = cell_offsets[hash];
                let n_count = cell_counts[hash];

                for (var j: u32 = 0u; j < n_count; j = j + 1u) {
                    let other_idx = sorted_indices[start + j];
                    if (other_idx == idx) {
                        continue;  // Already counted self
                    }

                    let other_pos = particles_in[other_idx].pos.xyz;
                    let diff = pos - other_pos;
                    let r_sq = dot(diff, diff);

                    let mass = particles_in[other_idx].vel.w;
                    density = density + mass * poly6_kernel(r_sq, h);
                }
            }
        }
    }

    densities[idx] = max(density, 0.001);  // Avoid division by zero
}

// --------------------------------------------------------------------------
// SPH force computation (pass 2)
// --------------------------------------------------------------------------

@compute @workgroup_size(256)
fn compute_sph_forces(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    let count = arrayLength(&particles_in);
    if (idx >= count) {
        return;
    }

    if (params.sph_enabled < 0.5) {
        sph_forces[idx] = vec4<f32>(0.0);
        return;
    }

    let pos = particles_in[idx].pos.xyz;
    let vel = particles_in[idx].vel.xyz;
    let my_density = densities[idx];
    let h = params.smoothing_radius;
    let cell_size = h;
    let my_cell = sph_pos_to_cell(pos, cell_size);

    // Pressure from equation of state
    let my_pressure = params.gas_constant * (my_density - params.rest_density);

    var pressure_force = vec3<f32>(0.0);
    var viscosity_force = vec3<f32>(0.0);

    // Search 3x3x3 neighborhood
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let neighbor_cell = my_cell + vec3<i32>(dx, dy, dz);

                if (any(neighbor_cell < vec3<i32>(0)) ||
                    any(neighbor_cell >= vec3<i32>(i32(GRID_SIZE)))) {
                    continue;
                }

                let hash = sph_cell_to_hash(neighbor_cell);
                let start = cell_offsets[hash];
                let n_count = cell_counts[hash];

                for (var j: u32 = 0u; j < n_count; j = j + 1u) {
                    let other_idx = sorted_indices[start + j];
                    if (other_idx == idx) {
                        continue;
                    }

                    let other_pos = particles_in[other_idx].pos.xyz;
                    let other_vel = particles_in[other_idx].vel.xyz;
                    let other_density = densities[other_idx];
                    let other_mass = particles_in[other_idx].vel.w;

                    let diff = pos - other_pos;
                    let r = length(diff);

                    if (r < 0.0001 || r >= h) {
                        continue;
                    }

                    let dir = diff / r;

                    // Pressure force (spiky kernel gradient)
                    let other_pressure = params.gas_constant * (other_density - params.rest_density);
                    let pressure_term = (my_pressure + other_pressure) / (2.0 * other_density);
                    pressure_force = pressure_force - dir * other_mass * pressure_term * spiky_kernel_gradient(r, h);

                    // Viscosity force (viscosity kernel laplacian)
                    let vel_diff = other_vel - vel;
                    viscosity_force = viscosity_force + other_mass * vel_diff / other_density * viscosity_kernel_laplacian(r, h);
                }
            }
        }
    }

    // Scale forces
    pressure_force = pressure_force * params.pressure_strength;
    viscosity_force = viscosity_force * params.viscosity;

    // Surface tension (simplified: towards center of mass of neighbors)
    // This is a basic cohesion force, not full surface tension
    let surface_force = vec3<f32>(0.0);  // Placeholder for now

    let total = pressure_force + viscosity_force + surface_force;
    sph_forces[idx] = vec4<f32>(total, 0.0);
}
