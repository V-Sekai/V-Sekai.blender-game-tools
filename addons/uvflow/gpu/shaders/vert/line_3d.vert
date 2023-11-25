uniform mat4 u_ViewProjectionMatrix;

in vec3 position;
in float lineLength;

out float v_LineLength;

void main()
{
    v_LineLength = lineLength;
    gl_Position = u_ViewProjectionMatrix * vec4(position, 1.0f);
}