"""
shaders.py — the lenticular weave GLSL, extracted from the Odyssey 3D player.

The weave math (the `base`/crosstalk/phase/FilterSlope block) is BYTE-IDENTICAL to the verified
player shader. Do NOT edit the signs (`v2.x*rsq - 2.0*v2.y*(corrB-0.5) + corrA` and the `- 0.25`
phase offset) — that exact form is the ground-truth-validated one (median frac err 0.0355 cyc,
NCC +0.99 vs a hardware capture). The only thing removed here is the player's on-screen HUD
(the convergence bar, the tracking dot, the tuning sliders) — none of which is part of the weave.

Two fragment shaders, same weave, different source layout:
  FRAG         — two separate textures, one per eye  (uL = left view, uR = right view)
  FRAG_SCREEN  — one side-by-side texture split on the GPU (uSrc; left half / right half)

Per-vertex attributes av2/av3/av4 come from the oracle (see oracle.Oracle); the GPU
interpolates them across the quad. The correction textures uCorrA/uCorrB are the panel's
3DStackCorrection_A/B (or a neutral fallback).
"""

# Passthrough vertex shader: forwards uv + the three oracle attribute vectors to the fragment stage.
VERT = """
#version 330
in vec2 pos; in vec2 uv; in vec2 av2; in vec2 av3; in vec3 av4;
out vec2 fuv; out vec2 v2; out vec2 v3; out vec3 v4;
void main(){ gl_Position = vec4(pos, 0.0, 1.0); fuv = uv; v2 = av2; v3 = av3; v4 = av4; }
"""

# Two-texture weave: uL = left view, uR = right view.
FRAG = """
#version 330
uniform sampler2D uL, uR, uCorrA, uCorrB;
uniform vec2 uRes; uniform float uFS, uXTalkFac, uXTalkDyn, uContrast, uCorrAScale, uConv; uniform int uWeave;
in vec2 fuv; in vec2 v2; in vec2 v3; in vec3 v4;
out vec4 o;
void main(){
    if(uWeave==0){ o = vec4(texture(uL, fuv).rgb, 1.0); return; }   // 2D passthrough (left view) when weave off
    vec2 suv = vec2(gl_FragCoord.x/uRes.x, 1.0 - gl_FragCoord.y/uRes.y);   // screen UV (flip GL bottom-up) for corrections
    float corrA = texture(uCorrA, suv).r * uCorrAScale;
    float corrB = texture(uCorrB, suv).r;
    float rsq = inversesqrt(1.0 + dot(v3, v3));
    float base = v2.x*rsq - 2.0*v2.y*(corrB - 0.5) + corrA;        // ground-truth sign form -- DO NOT EDIT
    vec3 L = texture(uR, fuv).rgb, R = texture(uL, fuv + vec2(uConv, 0.0)).rgb;   // uL/uR swapped -> hardware eye order
    L = (L-0.5)*uContrast + 0.5; R = (R-0.5)*uContrast + 0.5;
    vec3 dRL = R - L;                                              // per-pixel crosstalk pre-distortion
    float xt = ((1.0 + dot(v3, v3)) * v2.y*v2.y) * uXTalkDyn + uXTalkFac;
    xt = xt/(1.0 - xt);
    vec3 Lp = L - xt*dRL; vec3 Rp = R + xt*dRL;
    vec3 outc;
    for(int c=0;c<3;c++){
        float phase = fract(base + v4[c] - 0.25);                  // view ordering -> matches hardware capture
        float t = 2.0*phase - 1.0;
        float w = clamp(-abs(t)*uFS + uFS*0.5 + 0.5, 0.0, 1.0);     // FilterSlope triangle
        outc[c] = mix(Rp[c], Lp[c], w);
    }
    o = vec4(outc, 1.0);
}
"""

# Side-by-side weave: one texture uSrc, split on the GPU (left half / right half).
FRAG_SCREEN = """
#version 330
uniform sampler2D uSrc, uCorrA, uCorrB;
uniform vec2 uRes; uniform float uFS, uXTalkFac, uXTalkDyn, uContrast, uCorrAScale, uConv;
uniform int uWeave, uSrcFlip, uSrcBGR, uSrcSwapLR;
in vec2 fuv; in vec2 v2; in vec2 v3; in vec3 v4;
out vec4 o;
vec3 srcHalf(vec2 uv, float xlo){            // sample one SBS half; xlo=0.0 left half, 0.5 right half
    vec2 s = vec2(xlo + uv.x*0.5, uv.y);
    if(uSrcFlip==1) s.y = 1.0 - s.y;         // source y-flip (top-origin textures)
    vec3 c = texture(uSrc, s).rgb;
    return (uSrcBGR==1) ? c.bgr : c;
}
void main(){
    if(uWeave==0){ o = vec4(srcHalf(fuv, 0.0), 1.0); return; }   // 2D passthrough = left SBS half
    vec2 suv = vec2(gl_FragCoord.x/uRes.x, 1.0 - gl_FragCoord.y/uRes.y);   // screen UV for corrections
    float corrA = texture(uCorrA, suv).r * uCorrAScale;
    float corrB = texture(uCorrB, suv).r;
    float rsq = inversesqrt(1.0 + dot(v3, v3));
    float base = v2.x*rsq - 2.0*v2.y*(corrB - 0.5) + corrA;      // ground-truth sign form -- DO NOT EDIT
    float lx = (uSrcSwapLR==1) ? 0.0 : 0.5;                      // which SBS half feeds each woven view
    float rx = (uSrcSwapLR==1) ? 0.5 : 0.0;                      // toggle to fix flipped/pseudoscopic depth
    vec3 L = srcHalf(fuv, lx);
    vec3 R = srcHalf(fuv + vec2(uConv, 0.0), rx);
    L = (L-0.5)*uContrast + 0.5; R = (R-0.5)*uContrast + 0.5;
    vec3 dRL = R - L;
    float xt = ((1.0 + dot(v3, v3)) * v2.y*v2.y) * uXTalkDyn + uXTalkFac;
    xt = xt/(1.0 - xt);
    vec3 Lp = L - xt*dRL; vec3 Rp = R + xt*dRL;
    vec3 outc;
    for(int c=0;c<3;c++){
        float phase = fract(base + v4[c] - 0.25);
        float t = 2.0*phase - 1.0;
        float w = clamp(-abs(t)*uFS + uFS*0.5 + 0.5, 0.0, 1.0);
        outc[c] = mix(Rp[c], Lp[c], w);
    }
    o = vec4(outc, 1.0);
}
"""
