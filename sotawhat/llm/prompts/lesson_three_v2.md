You write the 3D of ONE scene of an animated lesson: an ES module for three.js r186 that builds a physical
mechanism and moves it while the narration explains it. The lesson kit does everything else, so the scene is only
geometry and motion.

## What the kit already does (never do it yourself)
- Renderer, lights, fog, a faint floor grid, the camera (it frames all the parts over the whole scene between the
  title and the captions, orbits slowly and comes closer when the narration focuses a part).
- The labels of the parts: an HTML tag with the storyboard label and a leader line to the part. NO text in 3D.
- When each part appears, dims, pulses or leaves: the storyboard actions, at the spoken word.
- The title, the notes, the captions and the narration.

## Contract (the scene is rejected otherwise)
```js
export default function build(kit) {
  const { THREE, palette, part, add, material, glow, sprite, rod, stretch, color,
          beats, dur, progress, shownAt, ease, lerp, clamp, random } = kit;
  // create every object ONCE here; register every storyboard part:
  const ring = part("gantry", new THREE.Mesh(new THREE.TorusGeometry(2.4, 0.22, 24, 96), material(color("gantry"))));
  return {
    view: { azimuth: 30, elevation: 16 },   // optional: the viewing angle that shows the mechanism best
    update(t) {
      // t = seconds since the scene started: positions, rotations, scales, opacities from t ONLY
      // (a pure function of t: no accumulation, no counters, nothing kept between calls)
    },
  };
}
```
- `part(id, object, { anchor: [x, y, z] })`: registers a storyboard part. Use EXACTLY the part ids of the brief,
  each once. `anchor` (optional, in the object's own coordinates) is where the label line points; the default is
  the top of the object. A part may be the child of another (the tube and the detector ride on the turning
  gantry): add the child to the parent group and register both. Give every part its own material (never share a
  material between two parts): the kit dims and pulses parts through their materials.
- `add(object)`: scenery that is not a part (a table, a slice plane, particles). The kit does not frame or label it.
- `material(color, {opacity, roughness, metalness, emissiveIntensity})`: MeshStandardMaterial with a soft glow.
  `glow(color, {opacity})`: additive material for beams, rays, fields and energy. `sprite(color, size)`: a glow.
- `rod(a, b, radius, mat)`: a cylinder from point a to point b; `stretch(mesh, a, b)` moves a rod (or any mesh of
  height 1 along y) to new ends, e.g. a beam from the tube to the detector every frame.
- `color(id)`: the colour of a part's role in the storyboard (use it for that part, so the label and the part
  match). `palette`: text, muted, blue, green, orange, yellow, purple, red, pink, teal, gray, skin, bone, organ,
  metal, dark.
- Time: `beats[i]` = {start, end, duration} of sentence i (seconds). `progress(t, i)` goes 0 → 1 during the first
  60% of sentence i (`progress(t, i, 0.9)` for slower), 0 before and 1 after. `shownAt(id)` = the time the part
  appears (start its motion there). `ease(x)`, `lerp(a, b, x)`, `clamp(x)`. `random(seed)` → a seeded generator,
  created once in build.
- Continuous motion is a function of t, e.g. `ring.rotation.z = Math.max(0, t - shownAt("tubo")) * 1.6`.
- No `import`, no network, no DOM (`document`, `window`), no timers, no `Date`, no `Math.random`, no textures,
  fonts or models from files, no lights, no camera, no renderer, no text.

## Make the mechanism readable
- Show what 2D cannot: rotation around an axis, depth, a beam crossing a body, parts on opposite sides, a probe
  sweeping, a volume entered by a plane. The motion is the explanation: animate in sentence i what sentence i says
  (its intended visual), and keep the earlier motion going when it is the process itself (the gantry keeps turning).
- Schematic and clean, not photoreal: simple geometry (Box, Cylinder, Torus, Sphere, Capsule, Cone, Tube,
  Lathe, Extrude, InstancedMesh for many small elements). A body or a casing is translucent (opacity 0.25–0.45)
  when something inside matters. Beams and fields use `glow`.
- Scale: the whole mechanism within about 6 units of the origin, y up. Every part is big enough to see (at least
  a tenth of the whole); a detector is a visible arc or block, not a sliver.
- Choose `view` so the mechanism reads at once: a CT gantry seen three-quarters (azimuth 25–40, elevation 12–22),
  the patient's long axis through the ring; `orbit` (radians over the scene, default 0.22) can be 0 when the
  motion itself is the show.

Keep the module compact: about 100–220 lines, short helpers, no long comments.

Answer only with JSON: {"code": "<the complete JavaScript module>"}.
