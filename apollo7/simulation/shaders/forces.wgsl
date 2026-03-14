// forces.wgsl -- Attraction/repulsion, gravity, and wind forces.
//
// Gravity and wind are uniform directional forces applied to all particles.
// Attraction/repulsion uses a spatial hash grid for efficient neighbor lookup.
// This shader writes force contributions to an output buffer consumed by
// the integration pass.

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
// Bindings
// --------------------------------------------------------------------------

@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<storage, read_write> forces_out: array<vec4<f32>>;
@group(0) @binding(2) var<uniform> params: SimParams;

// Spatial hash grid for neighbor lookup
@group(0) @binding(3) var<storage, read> cell_counts: array<u32>;
@group(0) @binding(4) var<storage, read> cell_offsets: array<u32>;
@group(0) @binding(5) var<storage, read> sorted_indices: array<u32>;

// --------------------------------------------------------------------------
// Spatial hash constants
// --------------------------------------------------------------------------

const GRID_SIZE: u32 = 128u;
const GRID_OFFSET: f32 = 64.0;   // Half of GRID_SIZE, centers grid at origin

// --------------------------------------------------------------------------
// Spatial hash helpers
// --------------------------------------------------------------------------

fn pos_to_cell(pos: vec3<f32>, cell_size: f32) -> vec3<i32> {
    return vec3<i32>(floor((pos + vec3<f32>(GRID_OFFSET)) / cell_size));
}

fn cell_to_hash(cell: vec3<i32>) -> u32 {
    // Wrap cell coordinates to grid bounds
    let cx = u32(cell.x) % GRID_SIZE;
    let cy = u32(cell.y) % GRID_SIZE;
    let cz = u32(cell.z) % GRID_SIZE;
    return cx + cy * GRID_SIZE + cz * GRID_SIZE * GRID_SIZE;
}

// --------------------------------------------------------------------------
// Force computation
// --------------------------------------------------------------------------

fn compute_forces(pos: vec3<f32>, vel: vec3<f32>, p: SimParams) -> vec3<f32> {
    var force = vec3<f32>(0.0);

    // Gravity (uniform directional)
    force = force + p.gravity.xyz;

    // Wind (uniform directional with noise modulation)
    let wind_turbulence = perlin3d(pos * 0.5 + vec3<f32>(p.time * 0.3)) * 0.2;
    force = force + p.wind.xyz * (1.0 + wind_turbulence);

    // Attraction/repulsion via spatial hash neighbor search
    let cell_size = p.repulsion_radius * 2.0;
    let my_cell = pos_to_cell(pos, cell_size);

    // Search 3x3x3 neighborhood
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let neighbor_cell = my_cell + vec3<i32>(dx, dy, dz);

                // Skip cells outside grid bounds
                if (any(neighbor_cell < vec3<i32>(0)) ||
                    any(neighbor_cell >= vec3<i32>(i32(GRID_SIZE)))) {
                    continue;
                }

                let hash = cell_to_hash(neighbor_cell);
                let start = cell_offsets[hash];
                let count = cell_counts[hash];

                for (var j: u32 = 0u; j < count; j = j + 1u) {
                    let other_idx = sorted_indices[start + j];
                    let other_pos = particles_in[other_idx].pos.xyz;

                    let diff = other_pos - pos;
                    let dist = length(diff);

                    if (dist < 0.0001) {
                        continue;  // Skip self
                    }

                    let dir = diff / dist;

                    // Repulsion (within repulsion radius)
                    if (dist < p.repulsion_radius) {
                        let repulsion = -dir * p.repulsion_strength * (1.0 - dist / p.repulsion_radius);
                        force = force + repulsion;
                    }

                    // Attraction (beyond repulsion radius, within 2x radius)
                    if (dist > p.repulsion_radius && dist < p.repulsion_radius * 4.0) {
                        let attraction = dir * p.attraction_strength / (dist * dist + 0.01);
                        force = force + attraction;
                    }
                }
            }
        }
    }

    return force;
}

// --------------------------------------------------------------------------
// Main compute entry point
// --------------------------------------------------------------------------

@compute @workgroup_size(256)
fn compute_external_forces(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    let count = arrayLength(&particles_in);
    if (idx >= count) {
        return;
    }

    let p_in = particles_in[idx];
    let force = compute_forces(p_in.pos.xyz, p_in.vel.xyz, params);

    // Accumulate with existing forces (flow field may have written already)
    let existing = forces_out[idx];
    forces_out[idx] = existing + vec4<f32>(force, 0.0);
}
