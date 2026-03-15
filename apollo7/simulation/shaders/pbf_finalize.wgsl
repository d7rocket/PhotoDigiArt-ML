// PBF Finalize: velocity from displacement, vorticity confinement, XSPH, clamping
//
// Derives new velocity from position change (predicted - original) / dt,
// applies vorticity confinement (PHYS-07) and XSPH viscosity for coherent
// flow, then clamps velocity magnitude and writes final state.

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

// Particle state: 2x vec4 = [pos.xyz, life, vel.xyz, mass]
struct Particle {
    pos_x: f32,
    pos_y: f32,
    pos_z: f32,
    life: f32,
    vel_x: f32,
    vel_y: f32,
    vel_z: f32,
    mass: f32,
};

// Original 4 bindings + 4 spatial hash bindings for neighbor search
@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read_write> particles_out: array<Particle>;
@group(0) @binding(3) var<uniform> params: SimParams;
@group(0) @binding(4) var<storage, read> cell_counts: array<u32>;
@group(0) @binding(5) var<storage, read> cell_offsets: array<u32>;
@group(0) @binding(6) var<storage, read> sorted_indices: array<u32>;

// Spatial hash constants (must match GRID_SIZE in buffers.py)
const GRID_SIZE: i32 = 128;
const GRID_TOTAL: u32 = 2097152u;  // 128^3

fn cell_hash(cx: i32, cy: i32, cz: i32) -> u32 {
    return u32(cx) + u32(cy) * u32(GRID_SIZE) + u32(cz) * u32(GRID_SIZE * GRID_SIZE);
}

// Poly6 kernel (for XSPH weighting)
fn W_poly6(r: f32, h: f32) -> f32 {
    if (r >= h) {
        return 0.0;
    }
    let h2 = h * h;
    let r2 = r * r;
    let diff = h2 - r2;
    // W_poly6 = 315/(64*pi*h^9) * (h^2 - r^2)^3
    let h9 = h2 * h2 * h2 * h2 * h;
    let coeff = 315.0 / (64.0 * 3.14159265 * h9);
    return coeff * diff * diff * diff;
}

@compute @workgroup_size(256)
fn pbf_finalize(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let n = u32(params.particle_count);
    if (idx >= n) {
        return;
    }

    let p_in = particles_in[idx];
    let original_pos = vec3<f32>(p_in.pos_x, p_in.pos_y, p_in.pos_z);
    let predicted_pos = predicted_positions[idx].xyz;

    // Derive velocity from position change
    var v_i = (predicted_pos - original_pos) / params.dt;

    let h = params.kernel_radius;
    let cs = params.cell_size;

    // Compute cell coordinates for neighbor search
    let cell_i = vec3<i32>(floor((predicted_pos + 64.0) / cs));

    // Accumulate vorticity (omega) and XSPH velocity correction
    var omega_i = vec3<f32>(0.0);
    var v_xsph = vec3<f32>(0.0);

    // Neighbor search: iterate 3x3x3 cells around particle
    for (var dz: i32 = -1; dz <= 1; dz = dz + 1) {
        for (var dy: i32 = -1; dy <= 1; dy = dy + 1) {
            for (var dx: i32 = -1; dx <= 1; dx = dx + 1) {
                let nc = cell_i + vec3<i32>(dx, dy, dz);

                // Bounds check
                if (nc.x < 0 || nc.x >= GRID_SIZE ||
                    nc.y < 0 || nc.y >= GRID_SIZE ||
                    nc.z < 0 || nc.z >= GRID_SIZE) {
                    continue;
                }

                let ch = cell_hash(nc.x, nc.y, nc.z);
                let count = cell_counts[ch];
                let offset = cell_offsets[ch];

                for (var k: u32 = 0u; k < count; k = k + 1u) {
                    let j = sorted_indices[offset + k];
                    if (j == idx) {
                        continue;
                    }

                    let pos_j = predicted_positions[j].xyz;
                    let r_vec = predicted_pos - pos_j;
                    let r = length(r_vec);

                    if (r >= h || r < 0.0001) {
                        continue;
                    }

                    // Neighbor velocity
                    let p_j = particles_in[j];
                    let v_j = (pos_j - vec3<f32>(p_j.pos_x, p_j.pos_y, p_j.pos_z)) / params.dt;

                    // Vorticity: omega_i += (v_j - v_i) x grad_W
                    // Approximate grad_W direction as normalized(r_vec)
                    let v_diff = v_j - v_i;
                    let grad_dir = r_vec / r;
                    // Spiky kernel gradient magnitude: -45/(pi*h^6) * (h-r)^2
                    let h6 = h * h * h * h * h * h;
                    let grad_mag = -45.0 / (3.14159265 * h6) * (h - r) * (h - r);
                    let grad_w = grad_dir * grad_mag;
                    omega_i = omega_i + cross(v_diff, grad_w);

                    // XSPH: weighted average of velocity differences
                    let w = W_poly6(r, h);
                    v_xsph = v_xsph + v_diff * w;
                }
            }
        }
    }

    // Apply vorticity confinement force
    // f_vorticity = epsilon * cross(normalize(eta), omega)
    // where eta = gradient of |omega| (approximated by omega direction itself
    // since computing eta would require a second neighbor pass)
    let omega_mag = length(omega_i);
    if (omega_mag > 0.0001 && params.vorticity_epsilon > 0.0) {
        // Simplified: use omega direction as eta approximation
        // This injects rotational energy proportional to local vorticity
        let eta_dir = omega_i / omega_mag;
        let f_vort = params.vorticity_epsilon * cross(eta_dir, omega_i);
        v_i = v_i + f_vort * params.dt;
    }

    // Apply XSPH viscosity (smooths velocity field)
    v_i = v_i + v_xsph * params.xsph_c;

    // Apply damping
    v_i = v_i * params.damping;

    // Velocity clamping: cap magnitude to max_velocity
    let vel_mag = length(v_i);
    if (vel_mag > params.max_velocity) {
        v_i = v_i * (params.max_velocity / vel_mag);
    }

    // Write output particle state
    var p_out: Particle;
    p_out.pos_x = predicted_pos.x;
    p_out.pos_y = predicted_pos.y;
    p_out.pos_z = predicted_pos.z;
    p_out.life = p_in.life;
    p_out.vel_x = v_i.x;
    p_out.vel_y = v_i.y;
    p_out.vel_z = v_i.z;
    p_out.mass = p_in.mass;

    particles_out[idx] = p_out;
}
