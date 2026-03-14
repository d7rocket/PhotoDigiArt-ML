// integrate.wgsl -- Combined force computation + integration pass.
//
// Computes Perlin noise flow field forces, gravity, and wind inline,
// then applies symplectic Euler integration and boundary clamping.
//
// Designed for chunked dispatch: workgroup_size(256), max 256K particles per dispatch.

// --------------------------------------------------------------------------
// Noise functions (inlined from noise.wgsl)
// --------------------------------------------------------------------------

fn mod289_3(x: vec3<f32>) -> vec3<f32> {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

fn mod289_4(x: vec4<f32>) -> vec4<f32> {
    return x - floor(x * (1.0 / 289.0)) * 289.0;
}

fn permute_4(x: vec4<f32>) -> vec4<f32> {
    return mod289_4(((x * 34.0) + 1.0) * x);
}

fn taylor_inv_sqrt_4(r: vec4<f32>) -> vec4<f32> {
    return 1.79284291400159 - 0.85373472095314 * r;
}

fn fade_3(t: vec3<f32>) -> vec3<f32> {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

fn perlin3d(P: vec3<f32>) -> f32 {
    var Pi0 = floor(P);
    var Pi1 = Pi0 + vec3<f32>(1.0);
    Pi0 = mod289_3(Pi0);
    Pi1 = mod289_3(Pi1);
    let Pf0 = fract(P);
    let Pf1 = Pf0 - vec3<f32>(1.0);

    let ix = vec4<f32>(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
    let iy = vec4<f32>(Pi0.y, Pi0.y, Pi1.y, Pi1.y);
    let iz0 = vec4<f32>(Pi0.z);
    let iz1 = vec4<f32>(Pi1.z);

    let ixy = permute_4(permute_4(ix) + iy);
    let ixy0 = permute_4(ixy + iz0);
    let ixy1 = permute_4(ixy + iz1);

    var gx0 = ixy0 * (1.0 / 7.0);
    var gy0 = fract(floor(gx0) * (1.0 / 7.0)) - 0.5;
    gx0 = fract(gx0);
    let gz0 = vec4<f32>(0.5) - abs(gx0) - abs(gy0);
    let sz0 = step(gz0, vec4<f32>(0.0));
    gx0 = gx0 - sz0 * (step(vec4<f32>(0.0), gx0) - 0.5);
    gy0 = gy0 - sz0 * (step(vec4<f32>(0.0), gy0) - 0.5);

    var gx1 = ixy1 * (1.0 / 7.0);
    var gy1 = fract(floor(gx1) * (1.0 / 7.0)) - 0.5;
    gx1 = fract(gx1);
    let gz1 = vec4<f32>(0.5) - abs(gx1) - abs(gy1);
    let sz1 = step(gz1, vec4<f32>(0.0));
    gx1 = gx1 - sz1 * (step(vec4<f32>(0.0), gx1) - 0.5);
    gy1 = gy1 - sz1 * (step(vec4<f32>(0.0), gy1) - 0.5);

    var g000 = vec3<f32>(gx0.x, gy0.x, gz0.x);
    var g100 = vec3<f32>(gx0.y, gy0.y, gz0.y);
    var g010 = vec3<f32>(gx0.z, gy0.z, gz0.z);
    var g110 = vec3<f32>(gx0.w, gy0.w, gz0.w);
    var g001 = vec3<f32>(gx1.x, gy1.x, gz1.x);
    var g101 = vec3<f32>(gx1.y, gy1.y, gz1.y);
    var g011 = vec3<f32>(gx1.z, gy1.z, gz1.z);
    var g111 = vec3<f32>(gx1.w, gy1.w, gz1.w);

    let norm0 = taylor_inv_sqrt_4(vec4<f32>(
        dot(g000, g000), dot(g010, g010), dot(g100, g100), dot(g110, g110)
    ));
    g000 = g000 * norm0.x;
    g010 = g010 * norm0.y;
    g100 = g100 * norm0.z;
    g110 = g110 * norm0.w;
    let norm1 = taylor_inv_sqrt_4(vec4<f32>(
        dot(g001, g001), dot(g011, g011), dot(g101, g101), dot(g111, g111)
    ));
    g001 = g001 * norm1.x;
    g011 = g011 * norm1.y;
    g101 = g101 * norm1.z;
    g111 = g111 * norm1.w;

    let n000 = dot(g000, Pf0);
    let n100 = dot(g100, vec3<f32>(Pf1.x, Pf0.yz));
    let n010 = dot(g010, vec3<f32>(Pf0.x, Pf1.y, Pf0.z));
    let n110 = dot(g110, vec3<f32>(Pf1.xy, Pf0.z));
    let n001 = dot(g001, vec3<f32>(Pf0.xy, Pf1.z));
    let n101 = dot(g101, vec3<f32>(Pf1.x, Pf0.y, Pf1.z));
    let n011 = dot(g011, vec3<f32>(Pf0.x, Pf1.yz));
    let n111 = dot(g111, Pf1);

    let fade_xyz = fade_3(Pf0);
    let n_z = mix(
        vec4<f32>(n000, n100, n010, n110),
        vec4<f32>(n001, n101, n011, n111),
        vec4<f32>(fade_xyz.z)
    );
    let n_yz = mix(n_z.xy, n_z.zw, vec2<f32>(fade_xyz.y));
    let n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
    return 2.2 * n_xyz;
}

fn fbm3d(p: vec3<f32>, octaves: u32) -> f32 {
    var value: f32 = 0.0;
    var amplitude: f32 = 0.5;
    var frequency: f32 = 1.0;
    var pos = p;
    for (var i: u32 = 0u; i < octaves; i = i + 1u) {
        value = value + amplitude * perlin3d(pos * frequency);
        frequency = frequency * 2.0;
        amplitude = amplitude * 0.5;
    }
    return value;
}

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

// --------------------------------------------------------------------------
// Force computation (inline -- no separate pass needed)
// --------------------------------------------------------------------------

fn compute_flow_force(pos: vec3<f32>, p: SimParams) -> vec3<f32> {
    let freq = p.noise_frequency;
    let amp = p.noise_amplitude;
    let oct = u32(p.noise_octaves);

    let sample_pos = pos * freq + vec3<f32>(p.time * 0.1);

    // Approximate curl noise by sampling noise at offset positions
    let eps = 0.01;
    let dx = fbm3d(sample_pos + vec3<f32>(eps, 0.0, 0.0), oct)
           - fbm3d(sample_pos - vec3<f32>(eps, 0.0, 0.0), oct);
    let dy = fbm3d(sample_pos + vec3<f32>(0.0, eps, 0.0), oct)
           - fbm3d(sample_pos - vec3<f32>(0.0, eps, 0.0), oct);
    let dz = fbm3d(sample_pos + vec3<f32>(0.0, 0.0, eps), oct)
           - fbm3d(sample_pos - vec3<f32>(0.0, 0.0, eps), oct);

    // Curl = cross product of gradient
    let curl = vec3<f32>(dy - dz, dz - dx, dx - dy) / (2.0 * eps);

    return curl * amp * p.turbulence_scale * p.speed;
}

fn compute_all_forces(pos: vec3<f32>, vel: vec3<f32>, p: SimParams) -> vec3<f32> {
    var force = vec3<f32>(0.0);

    // Flow field (Perlin noise curl)
    force = force + compute_flow_force(pos, p);

    // Gravity
    force = force + p.gravity.xyz;

    // Wind with noise modulation
    let wind_turb = perlin3d(pos * 0.5 + vec3<f32>(p.time * 0.3)) * 0.2;
    force = force + p.wind.xyz * (1.0 + wind_turb);

    return force;
}

// --------------------------------------------------------------------------
// Boundary clamping (soft bounce)
// --------------------------------------------------------------------------

const BOUNDARY: f32 = 50.0;
const BOUNCE_DAMPING: f32 = 0.5;

fn clamp_boundary(pos: vec3<f32>, vel: vec3<f32>) -> vec3<f32> {
    var v = vel;
    if (pos.x > BOUNDARY) { v.x = -abs(v.x) * BOUNCE_DAMPING; }
    if (pos.x < -BOUNDARY) { v.x = abs(v.x) * BOUNCE_DAMPING; }
    if (pos.y > BOUNDARY) { v.y = -abs(v.y) * BOUNCE_DAMPING; }
    if (pos.y < -BOUNDARY) { v.y = abs(v.y) * BOUNCE_DAMPING; }
    if (pos.z > BOUNDARY) { v.z = -abs(v.z) * BOUNCE_DAMPING; }
    if (pos.z < -BOUNDARY) { v.z = abs(v.z) * BOUNCE_DAMPING; }
    return v;
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

    // Compute all forces inline
    let force = compute_all_forces(pos, vel, params);

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
    vel = clamp_boundary(pos, vel);

    // Clamp position to boundary
    pos = clamp(pos, vec3<f32>(-BOUNDARY), vec3<f32>(BOUNDARY));

    // Write output
    var p_out: Particle;
    p_out.pos = vec4<f32>(pos, life);
    p_out.vel = vec4<f32>(vel, mass);
    particles_out[idx] = p_out;
}
