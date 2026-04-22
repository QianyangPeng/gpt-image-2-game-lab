/** 2D puppet-rig renderer.
 *
 * A skeleton is a tree of bones. Each bone has:
 *   - name, parent
 *   - offset [x, y]: where this bone's origin sits in its PARENT's coordinate space, in rest pose
 *   - sprite image ref (after loaded)
 *   - pivot [x, y]: the point within the SPRITE image that maps to this bone's origin
 *   - z: render order (lower = further back)
 *
 * A pose is a map boneName -> rotation in degrees.
 *
 * Animation is a list of keyframes [{ t: 0..1, pose: {...} }]. Linear interp between keyframes.
 */

export class PuppetRig {
  constructor({ skeleton, sprites, animations }) {
    this.skeleton = skeleton;               // array of bone defs
    this.sprites = sprites;                  // { boneName: Image }
    this.animations = animations;            // { animName: { duration, keyframes } }
    // Build name -> bone map for quick lookup
    this.bonesByName = {};
    for (const b of skeleton) this.bonesByName[b.name] = b;
  }

  // Evaluate animation at time t (seconds)
  poseAt(animName, t) {
    const anim = this.animations[animName];
    if (!anim) return {};
    const phase = (t % anim.duration) / anim.duration;   // 0..1
    const kfs = anim.keyframes;
    // Find surrounding keyframes (kfs sorted by t)
    let k0 = kfs[kfs.length - 1];
    let k1 = kfs[0];
    let t0 = k0.t - 1;   // wrap from previous cycle
    let t1 = k1.t;
    for (let i = 0; i < kfs.length; i++) {
      if (kfs[i].t > phase) {
        k1 = kfs[i];
        k0 = kfs[(i - 1 + kfs.length) % kfs.length];
        t1 = k1.t;
        t0 = k0.t;
        if (i === 0) t0 = k0.t - 1;
        break;
      }
    }
    if (phase >= kfs[kfs.length - 1].t) {
      // After last keyframe -- interpolate to first (wrapping)
      k0 = kfs[kfs.length - 1];
      k1 = kfs[0];
      t0 = k0.t;
      t1 = k1.t + 1;
    }
    const alpha = t1 === t0 ? 0 : (phase - t0) / (t1 - t0);
    const pose = {};
    const allBones = new Set([...Object.keys(k0.pose), ...Object.keys(k1.pose)]);
    for (const name of allBones) {
      const a = k0.pose[name] ?? 0;
      const b = k1.pose[name] ?? 0;
      pose[name] = a + (b - a) * alpha;
    }
    return pose;
  }

  // Compute world transform for a given bone, under a given pose.
  // Returns DOMMatrix.
  worldMatrix(boneName, pose, cache) {
    if (cache[boneName]) return cache[boneName];
    const bone = this.bonesByName[boneName];
    let m;
    if (bone.parent) {
      m = new DOMMatrix(this.worldMatrix(bone.parent, pose, cache));
    } else {
      m = new DOMMatrix();
    }
    m.translateSelf(bone.offset[0], bone.offset[1]);
    m.rotateSelf(pose[bone.name] || 0);
    cache[boneName] = m;
    return m;
  }

  /** Draw at (x, y) with optional facing (1 or -1) and scale. */
  render(ctx, animName, t, { x = 0, y = 0, facing = 1, scale = 1 } = {}) {
    const pose = this.poseAt(animName, t);
    const cache = {};

    ctx.save();
    ctx.translate(x, y);
    ctx.scale(facing * scale, scale);

    // Sort by z (back to front)
    const ordered = [...this.skeleton].sort((a, b) => (a.z || 0) - (b.z || 0));
    for (const bone of ordered) {
      const m = this.worldMatrix(bone.name, pose, cache);
      ctx.save();
      ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
      const img = this.sprites[bone.name];
      if (img && img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, -bone.pivot[0], -bone.pivot[1]);
      }
      ctx.restore();
    }
    ctx.restore();
  }

  /** Debug: draw bone hierarchy as lines so you can see it. */
  renderDebug(ctx, animName, t, { x = 0, y = 0, facing = 1, scale = 1 } = {}) {
    const pose = this.poseAt(animName, t);
    const cache = {};
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(facing * scale, scale);
    for (const bone of this.skeleton) {
      const m = this.worldMatrix(bone.name, pose, cache);
      ctx.save();
      ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
      // origin dot
      ctx.fillStyle = '#f9d36c';
      ctx.beginPath();
      ctx.arc(0, 0, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      // line from parent to this
      if (bone.parent) {
        const pM = this.worldMatrix(bone.parent, pose, cache);
        ctx.strokeStyle = 'rgba(249, 211, 108, 0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(pM.e, pM.f);
        ctx.lineTo(m.e, m.f);
        ctx.stroke();
      }
    }
    ctx.restore();
  }
}
