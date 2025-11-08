# visualizadorObj.py
# [mvfm] - Visualizador simples de modelos .OBJ com PyOpenGL
#
# Criado : 05/11/2025  || Última vez Alterado : 08/11/2025

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import numpy as np

# Variáveis globais
windowWidth, windowHeight = 800, 600
rotation = 0.0

vertices = []
faces = []
normais = []

mostrarNormais = False  # alterna com tecla 'n'

# Cache de normais calculadas (para evitar recálculo a cada frame)
normaisFaceCache = []

# Leitura do arquivo .OBJ
def carregarObjeto(caminho):
    """Lê um arquivo .OBJ e extrai vértices, normais e faces."""
    global vertices, faces, normais, normaisFaceCache
    vertices.clear()
    faces.clear()
    normais.clear()
    normaisFaceCache.clear()

    with open(caminho, 'r') as f:
        for linha in f:
            if linha.startswith('v '):
                _, x, y, z = linha.strip().split()
                vertices.append((float(x), float(y), float(z)))
            elif linha.startswith('vn '):
                _, x, y, z = linha.strip().split()
                normais.append((float(x), float(y), float(z)))
            elif linha.startswith('f '):
                partes = linha.strip().split()[1:]
                faceVertices, faceNormais = [], []
                for p in partes:
                    dados = p.split('/')
                    vIdx = int(dados[0]) - 1
                    faceVertices.append(vIdx)
                    if len(dados) >= 3 and dados[2]:
                        nIdx = int(dados[2]) - 1
                        faceNormais.append(nIdx)
                    else:
                        faceNormais.append(None)
                faces.append((faceVertices, faceNormais))

    # Pré-calcula as normais das faces que não possuem normais próprias
    for faceVertices, faceNormais in faces:
        if not any(n is not None for n in faceNormais):
            v1, v2, v3 = [np.array(vertices[i]) for i in faceVertices[:3]]
            normaisFaceCache.append(normalFace(v1, v2, v3))
        else:
            normaisFaceCache.append(None)

# Cálculo de normais
def normalFace(v1, v2, v3):
    """Calcula a normal de uma face a partir de 3 vértices."""
    u = v2 - v1
    v = v3 - v1
    n = np.cross(u, v)
    norma = np.linalg.norm(n)
    return (n / norma) if norma != 0 else np.array((0.0, 0.0, 1.0))

# Renderização do modelo
def desenharObjeto():
    """Renderiza o modelo carregado, usando normais por face ou vértice."""
    modo = glGetIntegerv(GL_POLYGON_MODE)[0]

    if modo == GL_FILL:
        glEnable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 1.0)
    else:
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 1.0, 0.0)

    glBegin(GL_TRIANGLES)
    for (faceVertices, faceNormais), normalCache in zip(faces, normaisFaceCache):
        temNormais = any(n is not None for n in faceNormais)

        # Usa a normal da cache se não houver normal associada
        if not temNormais and normalCache is not None:
            glNormal3fv(normalCache)

        for vIdx, nIdx in zip(faceVertices, faceNormais):
            if temNormais and nIdx is not None and nIdx < len(normais):
                glNormal3fv(normais[nIdx])
            glVertex3fv(vertices[vIdx])
    glEnd()

    # Desenho opcional das normais
    if mostrarNormais:
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 0.3, 1.0)
        glBegin(GL_LINES)
        for (faceVertices, faceNormais), normalCache in zip(faces, normaisFaceCache):
            for vIdx, nIdx in zip(faceVertices, faceNormais):
                v = np.array(vertices[vIdx])
                if nIdx is not None and nIdx < len(normais):
                    n = np.array(normais[nIdx])
                elif normalCache is not None:
                    n = normalCache
                else:
                    v1, v2, v3 = [np.array(vertices[i]) for i in faceVertices[:3]]
                    n = normalFace(v1, v2, v3)
                glVertex3fv(v)
                glVertex3fv(v + n * 0.2)
        glEnd()
        glEnable(GL_LIGHTING)

# HUD
def desenhaTexto(x, y, texto, r=0.0, g=1.0, b=1.0):
    depthEnabled = glIsEnabled(GL_DEPTH_TEST)
    if depthEnabled:
        glDisable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, windowWidth, 0, windowHeight)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor3f(r, g, b)
    glRasterPos2f(x, y)
    for c in texto:
        glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(c))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    if depthEnabled:
        glEnable(GL_DEPTH_TEST)

# Câmera e exibição
cameraPos = [0.0, 5.0, 5.0]
altVisao = 0.0

def display():
    global rotation
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    gluLookAt(cameraPos[0], cameraPos[1], cameraPos[2],
              0, altVisao, 0,
              0, 1, 0)

    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 10.0, 10.0, 1.0])

    glRotatef(rotation, 0, 1, 0)
    desenharObjeto()
    rotation = (rotation + 0.3) % 360

    glDisable(GL_LIGHTING)
    desenhaTexto(10, 10, f"Vértices: {len(vertices)} | Polígonos: {len(faces)}", 0.0, 1.0, 0.0)
    glEnable(GL_LIGHTING)

    glutSwapBuffers()

def redimensionar(w, h):
    h = max(h, 1)
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

# Inicialização
def inicializar():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.05, 0.05, 0.05, 1.0)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    luzDifusa = [0.9, 0.9, 0.9, 1.0]
    luzAmbiente = [0.3, 0.3, 0.3, 1.0]
    luzEspecular = [0.8, 0.8, 0.8, 1.0]
    luzPosicao = [5.0, 10.0, 5.0, 1.0]

    glLightfv(GL_LIGHT0, GL_DIFFUSE, luzDifusa)
    glLightfv(GL_LIGHT0, GL_AMBIENT, luzAmbiente)
    glLightfv(GL_LIGHT0, GL_SPECULAR, luzEspecular)
    glLightfv(GL_LIGHT0, GL_POSITION, luzPosicao)

    matDifusa = [1.0, 1.0, 1.0, 1.0]
    matSpecular = [1.0, 1.0, 1.0, 1.0]
    matShininess = [64.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, matDifusa)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, matSpecular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, matShininess)

# Entrada do teclado
def teclado(key, x, y):
    global cameraPos, mostrarNormais
    step = 0.3

    if key == b'q':
        cameraPos[1] += step
    elif key == b'e':
        cameraPos[1] -= step
    elif key == b'w':
        modo = glGetIntegerv(GL_POLYGON_MODE)[0]
        glPolygonMode(GL_FRONT_AND_BACK,
                      GL_LINE if modo == GL_FILL else
                      GL_POINT if modo == GL_LINE else
                      GL_FILL)
    elif key == b'n':
        mostrarNormais = not mostrarNormais


def specialKeys(key, x, y):
    global cameraPos, altVisao
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

# Execução principal
def main():
    if len(sys.argv) < 2:
        print("Uso: python visualizadorObj.py modelo.obj")
        sys.exit(1)

    caminhoObj = sys.argv[1]
    carregarObjeto(caminhoObj)

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(windowWidth, windowHeight)
    glutCreateWindow(b"Visualizador .OBJ [mvfm]")

    inicializar()
    glutDisplayFunc(display)
    glutIdleFunc(display)
    glutReshapeFunc(redimensionar)
    glutKeyboardFunc(teclado)
    glutSpecialFunc(specialKeys)
    glutMainLoop()


if __name__ == "__main__":
    main()
