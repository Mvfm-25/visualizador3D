# visualizador_obj.py
# [mvfm] - Esboço simples para visualização de modelos .OBJ com PyOpenGL

# Criado : 05/11/2025  || Última vez Alterado : 06/11/2025

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import sys
import numpy as np

# Variáveis globais
window_width, window_height = 800, 600
rotation = 0.0

vertices = []
faces = []
normais = []

def carregar_objeto(caminho):
    """Lê um arquivo .obj e extrai vértices, normais e faces simples."""
    global vertices, faces, normais
    vertices.clear()
    faces.clear()
    normais.clear()

    with open(caminho, 'r') as f:
        for linha in f:
            if linha.startswith('v '):  # vértice
                _, x, y, z = linha.strip().split()
                vertices.append((float(x), float(y), float(z)))
            elif linha.startswith('vn '):  # normal
                _, x, y, z = linha.strip().split()
                normais.append((float(x), float(y), float(z)))
            elif linha.startswith('f '):  # face
                partes = linha.strip().split()[1:]
                face_vertices = []
                face_normais = []
                for p in partes:
                    dados = p.split('/')
                    v_idx = int(dados[0]) - 1
                    face_vertices.append(v_idx)

                    # verifica se há normal associada
                    if len(dados) >= 3 and dados[2] != '':
                        n_idx = int(dados[2]) - 1
                        face_normais.append(n_idx)
                    else:
                        face_normais.append(None)

                faces.append((face_vertices, face_normais))

def normal_face(v1, v2, v3):
    """Calcula a normal de uma face a partir de 3 vértices."""
    u = np.subtract(v2, v1)
    v = np.subtract(v3, v1)
    n = np.cross(u, v)
    norma = np.linalg.norm(n)
    if norma == 0:
        return (0.0, 0.0, 1.0)
    return n / norma

def desenhar_objeto():
    """Renderiza o modelo carregado, com suporte a normais por face ou por vértice."""
    modo = glGetIntegerv(GL_POLYGON_MODE)[0]
    if modo == GL_FILL:
        glColor3f(1.0, 1.0, 1.0)
    else:
        glColor3f(0.0, 1.0, 0.0)

    glBegin(GL_TRIANGLES)
    for face_vertices, face_normais in faces:
        v1, v2, v3 = [vertices[i] for i in face_vertices[:3]]

        # Se o modelo não tiver normais, calcula a normal da face
        if all(n is None for n in face_normais):
            n = normal_face(v1, v2, v3)
            glNormal3fv(n)

        for v_idx, n_idx in zip(face_vertices, face_normais):
            if n_idx is not None and n_idx < len(normais):
                glNormal3fv(normais[n_idx])
            glVertex3fv(vertices[v_idx])
    glEnd()


# Coordenadas da câmera. Para melhor modificação no teclado depois.
cameraPos = [0.0, 5.0, 5.0]
altVisao = 0

# Função para renderizar texto na tela.
def desenhaTexto(x, y, texto, r=0.0, g=1.0, b=1.0):

    # Desabilita profundidade só pro texto
    depth_enabled = glIsEnabled(GL_DEPTH_TEST)
    if depth_enabled:
        glDisable(GL_DEPTH_TEST)

    #indo temporariamente para projeção 2D e rapidamente voltando.
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(r, g, b)
    glRasterPos2f(x,y)

    for c in texto :
        glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(c))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # Reativa profundidade se estava ativa
    if depth_enabled:
        glEnable(GL_DEPTH_TEST)

def display():
    """Função principal de desenho."""
    global rotation
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Posicionamento da câmera
    gluLookAt(cameraPos[0], cameraPos[1], cameraPos[2],   # posição da câmera
              0, altVisao, 0,   # para onde olha
              0, 1, 0)   # vetor 'up'

    # Para luz não se mover junto com o modelo.
    luzPosicao = [0.0, 10.0, 10.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, luzPosicao)

    # Só depois disso gira o modelo.
    glRotatef(rotation, 0, 1, 0)
    desenhar_objeto()

    lighting_enabled = glIsEnabled(GL_LIGHTING)
    if lighting_enabled:
        glDisable(GL_LIGHTING)

    rotation += 0.3

    # Chamando texto para ser printado no canto inferior esquerdo da tela.
    numFaces = len(faces)
    numVert = len(vertices)

    texto = f"Vértices : {numVert} | Polígonos : {numFaces}"
    desenhaTexto(10, 10, texto, 0.0, 1.0, 0.0)

    if lighting_enabled:
        glEnable(GL_LIGHTING)

    glutSwapBuffers()


def redimensionar(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

def inicializar():
    glEnable(GL_DEPTH_TEST)
    # Tratamento de normais
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.1, 0.1, 0.1, 1.0)

    # Iluminação simples
    glEnable(GL_LIGHTING)   # Habilita sistema de iluminação
    glEnable(GL_LIGHT0)     # 'Liga' a luz.

    # Definindo cor da luz. Neste caso, branco.
    luzDifusa = [1.0, 1.0, 1.0, 1.0]
    luzAmbiente = [0.2, 0.2, 0.2, 1.0]
    luzPosicao = [0.0, 10.0, 10.0, 1.0]  # Posição acima e um pouco à frente do modelo

    glLightfv(GL_LIGHT0, GL_DIFFUSE, luzDifusa)
    glLightfv(GL_LIGHT0, GL_AMBIENT, luzAmbiente)

    # Definição de material do modelo.
    matDifusa = [1.0, 1.0, 1.0, 1.0]
    matSpecular = [1.0, 1.0, 1.0, 1.0]
    matShininess = [50.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, matDifusa)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, matSpecular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, matShininess)

# alterna entre sólido / wireframe / pontos
def teclado(key, x, y):
    global cameraPos
    step = 0.3

    if key == b'q':
        cameraPos[1] += step
    elif key == b'e':
        cameraPos[1] -= step
    elif key == b'w':
        modo = glGetIntegerv(GL_POLYGON_MODE)[0]
        if modo == GL_FILL:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif modo == GL_LINE:
            glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

def special_keys(key, x, y):
    global cameraPos
    global altVisao
    step = 0.3
    if key == GLUT_KEY_UP:
        cameraPos[2] -= step
    elif key == GLUT_KEY_DOWN:
        cameraPos[2] += step
    elif key == GLUT_KEY_LEFT:
        altVisao -= step
    elif key == GLUT_KEY_RIGHT:
        altVisao += step
    glutPostRedisplay()

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
    glutSpecialFunc(special_keys)
    glutMainLoop()

if __name__ == "__main__":
    main()
