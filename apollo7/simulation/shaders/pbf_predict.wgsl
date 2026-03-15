// PBF Predict Pass: apply external forces, compute predicted positions
//
// Reads current position/velocity, applies home attraction + gravity,
// clamps force and velocity, writes predicted position.
// Curl noise will be added in Plan 04.

struct SimParams {
    // vec4 0: noise
    noise_frequency: f32,
    noise_amplitude: f32,
    noise_octaves: f32,
    turbulence_scale: f32,
    // vec4 1: home / breathing
    home_strength: f32,
    breathing_rate: f32,
    breathing_amplitude: f32,
    breathing_mod: f32,
    // vec4 2: PBF solver core
    kernel_radius: f32,
    rest_density: f32,
    epsilon_pbf: f32,
    solver_iterations: f32,
    // vec4 3: artificial pressure / XSPH
    artificial_pressure_k: f32,
    artificial_pressure_n: f32,
    delta_q: f32,
    xsph_c: f32,
    // vec4 4: stability
    vorticity_epsilon: f32,
    max_force: f32,
    max_velocity: f32,
    dt: f32,
    // vec4 5: gravity + damping
    gravity_x: f32,
    gravity_y: f32,
    gravity_z: f32,
    damping: f32,
    // vec4 6: wind + speed
    wind_x: f32,
    wind_y: f32,
    wind_z: f32,
    speed: f32,
    // vec4 7: runtime
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
@group(0) @binding(1) var<storage, read_write> predicted_out: array<vec4<f32>>;
@group(0) @binding(2) var<storage, read> home_positions: array<vec4<f32>>;
@group(0) @binding(3) var<uniform> params: SimParams;

@compute @workgroup_size(256)
fn pbf_predict(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    let n = u32(params.particle_count);
    if (idx >= n) {
        return;
    }

    let p = particles_in[idx];
    let pos = vec3<f32>(p.pos_x, p.pos_y, p.pos_z);
    var vel = vec3<f32>(p.vel_x, p.vel_y, p.vel_z);

    // Home attraction: elastic tether toward home position
    let home = home_positions[idx];
    let home_pos = home.xyz;
    let feature_strength = home.w;  // w = feature modulation (default 1.0)

    let displacement = home_pos - pos;
    let dist = length(displacement);
    var home_force = vec3<f32>(0.0);
    if (dist > 0.0001) {
        let dir = displacement / dist;
        let effective_strength = params.home_strength * params.breathing_mod * feature_strength;
        home_force = dir * effective_strength * dist;
    }

    // Gravity
    let gravity = vec3<f32>(params.gravity_x, params.gravity_y, params.gravity_z);

    // Total external force
    var force = home_force + gravity;

    // Force clamping: cap magnitude to max_force
    let force_mag = length(force);
    if (force_mag > params.max_force) {
        force = force * (params.max_force / force_mag);
    }

    // Update velocity: v += dt * force
    vel = vel + params.dt * force;

    // Velocity clamping: cap magnitude to max_velocity
    let vel_mag = length(vel);
    if (vel_mag > params.max_velocity) {
        vel = vel * (params.max_velocity / vel_mag);
    }

    // Predicted position: x_pred = x + dt * v
    let pred_pos = pos + params.dt * vel;

    // Write predicted position (w = 0 for padding, velocity stored in particles_in)
    predicted_out[idx] = vec4<f32>(pred_pos, 0.0);
}
