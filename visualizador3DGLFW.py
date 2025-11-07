# visualizador_obj_glfw.py
# [mvfm] - Visualizador de modelos .OBJ com PyOpenGL + GLFW
# Criado : 06/11/2025

import glfw
from OpenGL.GL import *
from OpenGL.GLU import *
import sys

# Variáveis globais
window_width, window_height = 800, 600
rotation = 0.0
vertices = []
faces = []

cameraPos = [0.0, 5.0, 5.0]
altVisao = 0.0
modo = GL_FILL  # modo de desenho (sólido / wireframe / pontos)


def carregar_objeto(caminho):
    """Lê um arquivo .obj e extrai vértices e faces simples (sem materiais/texturas)."""
    global vertices, faces
    with open(caminho, 'r') as f:
        for linha in f:
            if linha.startswith('v '):
                _, x, y, z = linha.strip().split()
                vertices.append((float(x), float(y), float(z)))
            elif linha.startswith('f '):
                partes = linha.strip().split()[1:]
                face = [int(p.split('/')[0]) - 1 for p in partes]
                faces.append(face)


def desenhar_objeto():
    """Renderiza o modelo carregado."""
    glBegin(GL_TRIANGLES)
    for face in faces:
        for vert_idx in face:
            glVertex3fv(vertices[vert_idx])
    glEnd()


def inicializar():
    """Configurações básicas de OpenGL."""
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.1, 0.1, 0.1, 1.0)


def redimensionar(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)


def display():
    """Desenha a cena."""
    global rotation, cameraPos, altVisao, modo

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Câmera
    gluLookAt(cameraPos[0], cameraPos[1], cameraPos[2],
              0, altVisao, 0,
              0, 1, 0)

    glRotatef(rotation, 0, 1, 0)
    glPolygonMode(GL_FRONT_AND_BACK, modo)
    desenhar_objeto()

    rotation += 0.3


# Input de teclado GLFW
def key_callback(window, key, scancode, action, mods):
    global cameraPos, altVisao, modo

    if action == glfw.PRESS or action == glfw.REPEAT:
        step = 0.3
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)

        # Câmera
        elif key == glfw.KEY_Q:
            cameraPos[1] += step
        elif key == glfw.KEY_E:
            cameraPos[1] -= step
        elif key == glfw.KEY_UP:
            cameraPos[2] -= step
        elif key == glfw.KEY_DOWN:
            cameraPos[2] += step
        elif key == glfw.KEY_LEFT:
            altVisao -= step
        elif key == glfw.KEY_RIGHT:
            altVisao += step

        # Alternar modo de renderização
        elif key == glfw.KEY_W:
            if modo == GL_FILL:
                modo = GL_LINE
            elif modo == GL_LINE:
                modo = GL_POINT
            else:
                modo = GL_FILL


def main():
    if len(sys.argv) < 2:
        print("Uso: python visualizador_obj_glfw.py modelo.obj")
        sys.exit(1)

    caminho_obj = sys.argv[1]
    carregar_objeto(caminho_obj)

    if not glfw.init():
        print("Falha ao inicializar o GLFW")
        sys.exit(1)

    window = glfw.create_window(window_width, window_height, "Visualizador .OBJ [mvfm]", None, None)
    if not window:
        glfw.terminate()
        print("Falha ao criar janela GLFW")
        sys.exit(1)

    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)

    inicializar()
    redimensionar(window_width, window_height)

    # Loop principal
    while not glfw.window_should_close(window):
        display()
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
