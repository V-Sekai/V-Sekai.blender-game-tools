flat_color_pixel_fn = """
    vec4 getInsideColor(float distance, float isOutside) {
        // this is effectively: color = (isOutside ? fillColor : vec4(0.0))
        return mix(fillColor, vec4(0.0), isOutside);
    }
"""

texture_pixel_fn = """
    vec4 getInsideColor(float distance, float isOutside) {
        // fill transparent regions with color - https://gamedev.stackexchange.com/a/164523
        vec4 insideColor = texture(image, texCoord_interp);
        insideColor = (insideColor * insideColor.w) + (fillColor * (1 - insideColor.w));

        // this is effectively: color = (isOutside ? insideColor : vec4(0.0))
        return mix(insideColor, vec4(0.0), isOutside);
    }
"""

fragment_shader_common = """
    uniform vec4 fillColor;
    uniform vec4 borderColor;
    uniform float borderWidth;
    uniform float borderRadius;
    uniform float edgeSoftness;

    uniform vec2 size;
    uniform vec2 location;

    in vec3 pos;
    out vec4 FragColor;

    vec4 getInsideColor(float distance, float isOutside);
    
    // from https://iquilezles.org/articles/distfunctions
    float sdRoundBox(vec2 p, vec2 b, float r) {
        return length(max(abs(p) - b + r, 0.0)) - r;
    }

    float sdBox(vec2 p, vec2 b) {
        vec2 q = abs(p) - b;
        return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
    }

    vec4 applyBorder(float distance, float isOutside, vec4 insideColor) {
        float w = mix(borderWidth, edgeSoftness, isOutside);

        float smoothedAlpha = 1.0 - smoothstep(-edgeSoftness, edgeSoftness, abs(distance) - w);
        return mix(insideColor, vec4(borderColor.xyz, borderColor.a * smoothedAlpha), smoothedAlpha);
    }

    vec4 drawBox(vec2 fragCoord) {
        float distance = 0.0;
        if (borderRadius > 0.001) {
            distance = sdRoundBox(location - fragCoord.xy, size * 0.5, borderRadius);
        } else {
            distance = sdBox(location - fragCoord.xy, size/2.0);
        }

        float isOutside = step(0, distance); // 1 if outside, 0 if inside
        
        vec4 color = getInsideColor(distance, isOutside);
        if (borderWidth > 0.001) {
            color = applyBorder(distance, isOutside, color);
        }

        return color;
    }

    void main() {
        FragColor = drawBox(pos.xy);
    }
"""

FLAT_COLOR_RECTANGLE_SHADER = {
    "vertex": """
        uniform mat4 ModelViewProjectionMatrix;

        in vec3 position;
        out vec3 pos;

        void main() {
            pos = position;
            gl_Position = ModelViewProjectionMatrix * vec4(position, 1.0);
        }
    """,
    "fragment": fragment_shader_common + "\n" + flat_color_pixel_fn,
}

TEXTURE_RECTANGLE_SHADER = {
    "vertex": """
        uniform mat4 ModelViewProjectionMatrix;

        in vec2 texCoord;
        in vec3 position;
        out vec3 pos;
        out vec2 texCoord_interp;

        void main() {
            pos = position;
            gl_Position = ModelViewProjectionMatrix * vec4(position, 1.0);
            texCoord_interp = texCoord;
        }
    """,
    "fragment": """
        uniform sampler2D image;
        in vec2 texCoord_interp;
    """
    + fragment_shader_common
    + "\n"
    + texture_pixel_fn,
}
