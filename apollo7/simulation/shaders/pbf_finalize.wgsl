// PBF Finalize: compute velocity from displacement, apply clamping, update output
//
// Derives new velocity from position change (predicted - original) / dt,
// clamps velocity magnitude, and writes final state to output buffer.
// Vorticity confinement and XSPH will be added in Plan 04.

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

@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<storage, read> predicted_positions: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read_write> particles_out: array<Particle>;
@group(0) @binding(3) var<uniform> params: SimParams;

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
    var v_new = (predicted_pos - original_pos) / params.dt;

    // Apply damping
    v_new = v_new * params.damping;

    // Velocity clamping: cap magnitude to max_velocity
    let vel_mag = length(v_new);
    if (vel_mag > params.max_velocity) {
        v_new = v_new * (params.max_velocity / vel_mag);
    }

    // Write output particle state
    var p_out: Particle;
    p_out.pos_x = predicted_pos.x;
    p_out.pos_y = predicted_pos.y;
    p_out.pos_z = predicted_pos.z;
    p_out.life = p_in.life;
    p_out.vel_x = v_new.x;
    p_out.vel_y = v_new.y;
    p_out.vel_z = v_new.z;
    p_out.mass = p_in.mass;

    particles_out[idx] = p_out;
}
