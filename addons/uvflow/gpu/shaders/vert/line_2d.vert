uniform mat4 ModelViewProjectionMatrix;

in vec2 position;
in float lineLength;

out float v_LineLength;

void main()
{
    v_LineLength = lineLength;
    gl_Position = ModelViewProjectionMatrix * vec4(position, 1.0f, 1.0f);
}