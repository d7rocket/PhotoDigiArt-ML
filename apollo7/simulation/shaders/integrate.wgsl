// integrate.wgsl -- Final integration pass for particle simulation.
//
// Reads accumulated force contributions, applies symplectic Euler integration,
// clamps boundaries, writes to output particle buffer.
//
// Designed for chunked dispatch: workgroup_size(256), max 256K particles per dispatch.

// --------------------------------------------------------------------------
// Shared struct definitions (must match Python-side packing exactly)
// --------------------------------------------------------------------------

struct Particle {
    pos: vec4<f32>,  // xyz = position, w = life
    vel: vec4<f32>,  // xyz = velocity, w = mass
};

struct SimParams {
    // vec4 0
    noise_frequency: f32,
    noise_amplitude: f32,
    noise_octaves: f32,
    turbulence_scale: f32,
    // vec4 1
    viscosity: f32,
    pressure_strength: f32,
    surface_tension: f32,
    attraction_strength: f32,
    // vec4 2
    repulsion_strength: f32,
    repulsion_radius: f32,
    smoothing_radius: f32,
    rest_density: f32,
    // vec4 3
    gas_constant: f32,
    speed: f32,
    dt: f32,
    damping: f32,
    // vec4 4
    gravity: vec4<f32>,   // xyz = gravity direction, w = pad
    // vec4 5
    wind: vec4<f32>,      // xyz = wind direction, w = pad
    // vec4 6
    time: f32,
    sph_enabled: f32,
    performance_mode: f32,
    _pad2: f32,
};

// --------------------------------------------------------------------------
// Bindings
// --------------------------------------------------------------------------

@group(0) @binding(0) var<storage, read> particles_in: array<Particle>;
@group(0) @binding(1) var<storage, read_write> particles_out: array<Particle>;
@group(0) @binding(2) var<uniform> params: SimParams;
@group(0) @binding(3) var<storage, read> forces_buf: array<vec4<f32>>;

// --------------------------------------------------------------------------
// Boundary clamping (soft bounce)
// --------------------------------------------------------------------------

const BOUNDARY: f32 = 50.0;
const BOUNCE_DAMPING: f32 = 0.5;

fn clamp_boundary(pos: vec3<f32>, vel: vec3<f32>) -> vec4<f32> {
    // Returns vec4(new_vel.xyz, 0.0) with soft bounce at boundaries
    var v = vel;
    var p = pos;

    if (p.x > BOUNDARY) { v.x = -abs(v.x) * BOUNCE_DAMPING; }
    if (p.x < -BOUNDARY) { v.x = abs(v.x) * BOUNCE_DAMPING; }
    if (p.y > BOUNDARY) { v.y = -abs(v.y) * BOUNCE_DAMPING; }
    if (p.y < -BOUNDARY) { v.y = abs(v.y) * BOUNCE_DAMPING; }
    if (p.z > BOUNDARY) { v.z = -abs(v.z) * BOUNCE_DAMPING; }
    if (p.z < -BOUNDARY) { v.z = abs(v.z) * BOUNCE_DAMPING; }

    return vec4<f32>(v, 0.0);
}

// --------------------------------------------------------------------------
// Main compute entry point
// --------------------------------------------------------------------------

@compute @workgroup_size(256)
fn integrate(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    let count = arrayLength(&particles_in);
    if (idx >= count) {
        return;
    }

    let p_in = particles_in[idx];
    var pos = p_in.pos.xyz;
    var vel = p_in.vel.xyz;
    let life = p_in.pos.w;
    let mass = p_in.vel.w;

    // Read accumulated forces
    let force = forces_buf[idx].xyz;

    // Symplectic Euler integration
    let dt = params.dt * params.speed;
    let acceleration = force / max(mass, 0.001);

    // Update velocity first (symplectic Euler)
    vel = vel + acceleration * dt;

    // Apply damping
    vel = vel * params.damping;

    // Update position
    pos = pos + vel * dt;

    // Boundary soft-bounce
    let bounced = clamp_boundary(pos, vel);
    vel = bounced.xyz;

    // Clamp position to boundary
    pos = clamp(pos, vec3<f32>(-BOUNDARY), vec3<f32>(BOUNDARY));

    // Write output
    var p_out: Particle;
    p_out.pos = vec4<f32>(pos, life);
    p_out.vel = vec4<f32>(vel, mass);
    particles_out[idx] = p_out;
}
