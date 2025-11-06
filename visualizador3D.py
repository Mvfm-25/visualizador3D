# visualizador_obj.py
# [mvfm] - Esboço simples para visualização de modelos .OBJ com PyOpenGL

# Criado : 05/11/2025  || Última vez Alterado : 06/11/2025

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys

# Variáveis globais
window_width, window_height = 800, 600
rotation = 0.0
vertices = []
faces = []

def carregar_objeto(caminho):
    """Lê um arquivo .obj e extrai vértices e faces simples (sem materiais/texturas)."""
    global vertices, faces
    with open(caminho, 'r') as f:
        for linha in f:
            if linha.startswith('v '):  # vértice
                _, x, y, z = linha.strip().split()
                vertices.append((float(x), float(y), float(z)))
            elif linha.startswith('f '):  # face
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

def display():
    """Função principal de desenho."""
    global rotation
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Posicionamento da câmera
    gluLookAt(0, 5, 5,   # posição da câmera
              0, 0, 0,   # para onde olha
              0, 1, 0)   # vetor 'up'

    glRotatef(rotation, 0, 1, 0)
    desenhar_objeto()

    rotation += 0.3
    glutSwapBuffers()

def redimensionar(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def inicializar():
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.1, 0.1, 0.1, 1.0)

# alterna entre sólido / wireframe / pontos
def teclado(key, x, y):
    if key == b'w':
        modo = glGetIntegerv(GL_POLYGON_MODE)[0]
        if modo == GL_FILL:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif modo == GL_LINE:
            glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)


def main():
    if len(sys.argv) < 2:
        print("Uso: python visualizador_obj.py modelo.obj")
        sys.exit(1)

    caminho_obj = sys.argv[1]
    carregar_objeto(caminho_obj)

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"Visualizador .OBJ [mvfm]")

    inicializar()
    glutDisplayFunc(display)
    glutIdleFunc(display)
    glutReshapeFunc(redimensionar)
    glutKeyboardFunc(teclado)
    glutMainLoop()

if __name__ == "__main__":
    main()
