// flow_field.wgsl -- Feature-driven flow field computation.
//
// Samples edge_map and depth_map textures to modulate Perlin noise flow.
// Edge intensity drives turbulence magnitude; depth drives current direction.
// Requires noise.wgsl functions (perlin3d, fbm3d) to be included before this file.

// --------------------------------------------------------------------------
// Struct definitions (must match integrate.wgsl / Python-side packing)
// --------------------------------------------------------------------------

struct Particle {
    pos: vec4<f32>,  // xyz = position, w = life
    vel: vec4<f32>,  // xyz = velocity, w = mass
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
@group(0) @binding(1) var<storage, read_write> flow_output: array<vec4<f32>>;
@group(0) @binding(2) var<uniform> params: SimParams;

// Feature textures (optional -- bound when available)
@group(1) @binding(0) var edge_map: texture_2d<f32>;
@group(1) @binding(1) var depth_map: texture_2d<f32>;
@group(1) @binding(2) var feature_sampler: sampler;

// --------------------------------------------------------------------------
// Feature texture sampling
// --------------------------------------------------------------------------

fn pos_to_uv(pos: vec3<f32>) -> vec2<f32> {
    // Map 3D position to 2D UV coordinates.
    // Assumes positions are roughly in [-1, 1] range (normalized).
    return vec2<f32>(pos.x * 0.5 + 0.5, pos.y * 0.5 + 0.5);
}

fn sample_edge_intensity(pos: vec3<f32>) -> f32 {
    let uv = pos_to_uv(pos);
    return textureSampleLevel(edge_map, feature_sampler, uv, 0.0).r;
}

fn sample_depth_value(pos: vec3<f32>) -> f32 {
    let uv = pos_to_uv(pos);
    return textureSampleLevel(depth_map, feature_sampler, uv, 0.0).r;
}

// --------------------------------------------------------------------------
// Flow field computation
// --------------------------------------------------------------------------

fn compute_flow(pos: vec3<f32>, time: f32, p: SimParams) -> vec3<f32> {
    // Base flow from Perlin noise (curl-noise-like via offset sampling)
    let freq = p.noise_frequency;
    let amp = p.noise_amplitude;
    let oct = u32(p.noise_octaves);

    let sample_pos = pos * freq + vec3<f32>(time * 0.1);

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

    // Feature-driven modulation
    let edge_val = sample_edge_intensity(pos);
    let depth_val = sample_depth_value(pos);

    // Edge intensity drives turbulence magnitude
    let turbulence = edge_val * p.turbulence_scale;

    // Depth drives a current in the Z direction
    let depth_current = vec3<f32>(0.0, 0.0, depth_val * 0.5 - 0.25);

    // Combine: base curl noise + feature-modulated turbulence + depth current
    return (curl * amp + curl * turbulence + depth_current) * p.speed;
}

// --------------------------------------------------------------------------
// Main compute entry point
// --------------------------------------------------------------------------

@compute @workgroup_size(256)
fn compute_flow_field(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let idx = global_id.x;
    let count = arrayLength(&particles_in);
    if (idx >= count) {
        return;
    }

    let pos = particles_in[idx].pos.xyz;
    let flow = compute_flow(pos, params.time, params);
    flow_output[idx] = vec4<f32>(flow, 0.0);
}
