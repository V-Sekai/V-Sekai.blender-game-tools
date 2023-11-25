uniform vec4 u_Color;
uniform float u_DashSize;
uniform float u_Spacing;

in float v_LineLength;
out vec4 outColor;

void main()
{   
    if (mod(v_LineLength, u_DashSize) > u_Spacing)
        outColor = vec4(pow(u_Color.rgb, vec3(4.0)), u_Color.a);
    else
        outColor = u_Color;
}