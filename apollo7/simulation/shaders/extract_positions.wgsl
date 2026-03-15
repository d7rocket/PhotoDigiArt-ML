// Extract positions from stride-32 particle state into packed vec4 buffer.
//
// Reads: particle state array (2x vec4 per particle: pos.xyz+life, vel.xyz+mass)
// Writes: packed positions buffer (vec4 per particle: pos.xyz, 1.0)
//
// This enables zero-copy GPU buffer sharing with pygfx by writing
// positions into a VERTEX-flagged buffer that pygfx can read directly.

struct Particle {
    pos_life: vec4<f32>,   // xyz = position, w = life
    vel_mass: vec4<f32>,   // xyz = velocity, w = mass
};

@group(0) @binding(0) var<storage, read> particles: array<Particle>;
@group(0) @binding(1) var<storage, read_write> positions_out: array<vec4<f32>>;

@compute @workgroup_size(256)
fn extract_positions(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;

    // Guard against out-of-bounds
    if (idx >= arrayLength(&particles)) {
        return;
    }

    let p = particles[idx];
    positions_out[idx] = vec4<f32>(p.pos_life.xyz, 1.0);
}
