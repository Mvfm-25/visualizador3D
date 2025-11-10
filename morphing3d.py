#!/usr/bin/env python3

#morphing3D.py
#[mvfm] - Morphing simples entre dois modelos .OBJ usando PyOpenGL
#
# Uso : bem como o uso do 'visualizador3D.py', mas agora se requer a especificação de dois modelos .obj

#Teclas:
#    m - pausar/retomar morphing
#    n - mostrar/ocultar normais
#    w/q - subir/descer câmera
#    setas - afastar/aprox., inclinar visão
#    s - avançar um passo de morph (quando pausado)
#    ESC - sair

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import numpy as np
import math

#Config e estados globais
windowWidth, windowHeight = 1024, 700
rotation = 0.0

# modelos: cada um é um dict com 'vertices' (lista de np.array), 'faces' (lista de [v_idx,...]), 'normals' (lista de np.array - opcionais)
modelA = None
modelB = None

# associações: lista onde assoc[i] = j significa que face i de A -> face j de B
associations = []

# controle do morphing
morph_t = 0.0
morph_dir = 1
animar = True
mostrarNormais = False

# câmera
cameraPos = [0.0, 0.0, 3.5]
altVisao = 0.0

#Utilitários OBJ

def carregar_obj(path):

    # Práticamente mesma implementação que 'visualizador3D.py' porém, de novo, estamos lidando com o DOBRO de modelos.
    verts = []
    faces = []
    normals = []

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.strip().split()
                if len(parts) >= 4:
                    x, y, z = map(float, parts[1:4])
                    verts.append(np.array((x, y, z), dtype=float))
            elif line.startswith('vn '):
                parts = line.strip().split()
                x, y, z = map(float, parts[1:4])
                normals.append(np.array((x, y, z), dtype=float))
            elif line.startswith('f '):
                parts = line.strip().split()[1:]
                # cada parte pode ser v, v/vt, v//vn, v/vt/vn
                idxs = []
                for p in parts:
                    if '/' in p:
                        v_idx = p.split('/')[0]
                    else:
                        v_idx = p
                    if v_idx == '':
                        continue
                    i = int(v_idx) - 1
                    idxs.append(i)
                # triangula se necessário
                if len(idxs) == 3:
                    faces.append(idxs)
                elif len(idxs) > 3:
                    # fan triangulation
                    for i in range(1, len(idxs) - 1):
                        faces.append([idxs[0], idxs[i], idxs[i + 1]])
                # faces com <3 ignoradas
    return {'vertices': verts, 'faces': faces, 'normals': normals}

# Normalização

def normalizar_modelo(model):
    v = np.array(model['vertices'])
    if v.size == 0:
        return
    centro = np.mean(v, axis=0)
    v -= centro
    max_dist = np.max(np.linalg.norm(v, axis=1))
    if max_dist == 0:
        max_dist = 1.0
    v /= max_dist
    model['vertices'] = [np.array(row) for row in v]

# Geometria e associação

def centroid_of_face(face, vertices):
    pts = np.array([vertices[i] for i in face])
    return np.mean(pts, axis=0)


def face_normal(face, vertices):
    a = np.array(vertices[face[0]])
    b = np.array(vertices[face[1]])
    c = np.array(vertices[face[2]])
    u = b - a
    v = c - a
    n = np.cross(u, v)
    norm = np.linalg.norm(n)
    if norm == 0:
        return np.array((0.0, 0.0, 1.0))
    return n / norm


def associate_faces(modelA, modelB):
    """Associa cada face de A a uma face de B pelo centróide mais próximo.
    Retorna lista assoc onde assoc[i] = j (índice de face em B)."""
    centA = [centroid_of_face(f, modelA['vertices']) for f in modelA['faces']]
    centB = [centroid_of_face(f, modelB['vertices']) for f in modelB['faces']]

    assoc = []
    if len(centB) == 0:
        return [None] * len(centA)

    # para cada centróide de A, encontra index de B com menor distância
    for c in centA:
        dists = [np.linalg.norm(c - cb) for cb in centB]
        j = int(np.argmin(dists))
        assoc.append(j)
    return assoc

# Interpolação e desenho

def desenhar_morph(t):
    """Desenha o morphed mesh: para cada face de A, pega a face associada em B e interpola os 3 vértices."""
    global modelA, modelB, associations

    glBegin(GL_TRIANGLES)
    for i, faceA in enumerate(modelA['faces']):
        j = associations[i] if i < len(associations) else None
        if j is None or j >= len(modelB['faces']):
            # sem par; desenha faceA pura (treat como t=0)
            verts = [modelA['vertices'][idx] for idx in faceA]
            n = face_normal(faceA, modelA['vertices'])
            glNormal3fv(n)
            for v in verts:
                glVertex3fv(v)
            continue

        faceB = modelB['faces'][j]
        vertsA = [modelA['vertices'][idx] for idx in faceA]
        vertsB = [modelB['vertices'][idx] for idx in faceB]

        # Caso faces tenham diferentes ordenações geométricas, tentamos alinhar os vértices pelo menor soma de distâncias
        vertsB_aligned = align_triangle_vertices(vertsA, vertsB)

        for va, vb in zip(vertsA, vertsB_aligned):
            v = (1 - t) * np.array(va) + t * np.array(vb)
            # normal por face aproximada (usando tri interpolado) - ok para iluminação simples
        tri = [(1 - t) * np.array(vertsA[0]) + t * np.array(vertsB_aligned[0]),
               (1 - t) * np.array(vertsA[1]) + t * np.array(vertsB_aligned[1]),
               (1 - t) * np.array(vertsA[2]) + t * np.array(vertsB_aligned[2])]
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        n_norm = np.linalg.norm(n)
        if n_norm == 0:
            n = np.array((0.0, 0.0, 1.0))
        else:
            n = n / n_norm
        glNormal3fv(n)
        for k in range(3):
            v = tri[k]
            glVertex3fv(v)
    glEnd()

    # desenha normais se pedido
    if mostrarNormais:
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        for i, face in enumerate(modelA['faces']):
            j = associations[i] if i < len(associations) else None
            vertsA = [modelA['vertices'][idx] for idx in face]
            if j is not None and j < len(modelB['faces']):
                vertsB = [modelB['vertices'][idx] for idx in modelB['faces'][j]]
                vertsB_aligned = align_triangle_vertices(vertsA, vertsB)
                tri = [(1 - morph_t) * np.array(vertsA[k]) + morph_t * np.array(vertsB_aligned[k]) for k in range(3)]
                center = np.mean(tri, axis=0)
                n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                n_norm = np.linalg.norm(n)
                if n_norm == 0:
                    n = np.array((0.0, 0.0, 1.0))
                else:
                    n = n / n_norm
            else:
                tri = [np.array(v) for v in vertsA]
                center = np.mean(tri, axis=0)
                n = face_normal(face, modelA['vertices'])
            glVertex3fv(center)
            glVertex3fv(center + n * 0.08)
        glEnd()
        glEnable(GL_LIGHTING)


def align_triangle_vertices(vertsA, vertsB):
    """Tenta alinhar a ordem dos vértices de vertsB para coincidir melhor com vertsA.
    Retorna lista de 3 pontos de vertsB em ordem alinhada."""
    # assume listas de 3 pontos cada (np.array ou alike)
    if len(vertsA) != 3 or len(vertsB) != 3:
        # fallback: se tamanhos diferentes, repete ou trunca
        # converte para arrays
        va = [np.array(v) for v in vertsA]
        vb = [np.array(v) for v in vertsB]
        while len(vb) < 3:
            vb.append(vb[-1].copy())
        return vb[:3]

    vb = [np.array(v) for v in vertsB]
    va = [np.array(v) for v in vertsA]

    best = vb
    best_cost = float('inf')
    # tenta as 3 rotações e a reversa
    permutations = [vb, [vb[1], vb[2], vb[0]], [vb[2], vb[0], vb[1]], [vb[2], vb[1], vb[0]], [vb[1], vb[0], vb[2]], [vb[0], vb[2], vb[1]]]
    for perm in permutations:
        cost = sum(np.linalg.norm(va[i] - perm[i]) for i in range(3))
        if cost < best_cost:
            best_cost = cost
            best = perm
    return best

# Métodos principais OpenGL para execução final.

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
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(c))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    if depthEnabled:
        glEnable(GL_DEPTH_TEST)


def display():
    global rotation, morph_t, morph_dir
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    gluLookAt(cameraPos[0], cameraPos[1], cameraPos[2], 0, altVisao, 0, 0, 1, 0)

    # luz
    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 5.0, 5.0, 1.0])

    glPushMatrix()
    glRotatef(rotation, 0, 1, 0)

    # desenha morph
    desenhar_morph(morph_t)

    glPopMatrix()

    # HUD
    glDisable(GL_LIGHTING)
    desenhaTexto(10, windowHeight - 20, f"Faces A: {len(modelA['faces'])} | Faces B: {len(modelB['faces'])}")
    desenhaTexto(10, windowHeight - 40, f"morph t: {morph_t:.3f} | anim: {animar} | n: toggle normais")
    glEnable(GL_LIGHTING)

    glutSwapBuffers()

    # atualização de estado
    if animar:
        morph_t += 0.006 * morph_dir
        if morph_t >= 1.0:
            morph_t = 1.0
            morph_dir = -1
        elif morph_t <= 0.0:
            morph_t = 0.0
            morph_dir = 1

    rotation = (rotation + 0.15) % 360


def redimensionar(w, h):
    global windowWidth, windowHeight
    h = max(h, 1)
    windowWidth, windowHeight = w, h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w / float(h), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)


def inicializar():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glClearColor(0.06, 0.06, 0.06, 1.0)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    luzDifusa = [0.95, 0.95, 0.95, 1.0]
    luzAmbiente = [0.25, 0.25, 0.25, 1.0]
    luzEspecular = [0.8, 0.8, 0.8, 1.0]
    luzPosicao = [5.0, 10.0, 5.0, 1.0]

    glLightfv(GL_LIGHT0, GL_DIFFUSE, luzDifusa)
    glLightfv(GL_LIGHT0, GL_AMBIENT, luzAmbiente)
    glLightfv(GL_LIGHT0, GL_SPECULAR, luzEspecular)
    glLightfv(GL_LIGHT0, GL_POSITION, luzPosicao)

    matDifusa = [1.0, 1.0, 1.0, 1.0]
    matSpecular = [1.0, 1.0, 1.0, 1.0]
    matShininess = [32.0]

    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, matDifusa)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, matSpecular)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, matShininess)


def teclado(key, x, y):
    global cameraPos, mostrarNormais, animar, morph_t
    if key == b'q':
        cameraPos[1] += 0.2
    elif key == b'e':
        cameraPos[1] -= 0.2
    elif key == b'w':
        cameraPos[2] -= 0.2
    elif key == b's':
        # se estiver pausado, avança um passo
        if not animar:
            morph_t = min(1.0, morph_t + 0.02)
    elif key == b'm':
        animar = not animar
    elif key == b'n':
        mostrarNormais = not mostrarNormais
    elif key == b'\x1b':  # ESC
        sys.exit(0)
    glutPostRedisplay()


def specialKeys(key, x, y):
    global cameraPos, altVisao
    step = 0.2
    if key == GLUT_KEY_UP:
        cameraPos[2] -= step
    elif key == GLUT_KEY_DOWN:
        cameraPos[2] += step
    elif key == GLUT_KEY_LEFT:
        altVisao -= 0.2
    elif key == GLUT_KEY_RIGHT:
        altVisao += 0.2
    glutPostRedisplay()

# ---------------------- Entrypoint ----------------------

def main():
    global modelA, modelB, associations
    if len(sys.argv) < 3:
        print("Uso: python morphing3D.py modeloA.obj modeloB.obj")
        sys.exit(1)

    pathA = sys.argv[1]
    pathB = sys.argv[2]

    modelA = carregar_obj(pathA)
    modelB = carregar_obj(pathB)

    if len(modelA['faces']) == 0 or len(modelB['faces']) == 0:
        print("Erro: um dos modelos não contém faces trianguladas ou está vazio.")
        sys.exit(1)

    # normaliza ambos
    normalizar_modelo(modelA)
    normalizar_modelo(modelB)

    # associa faces A -> B
    associations = associate_faces(modelA, modelB)

    # inicializa GLUT
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(windowWidth, windowHeight)
    glutCreateWindow(b"morphing3D - [mvfm]")

    inicializar()

    glutDisplayFunc(display)
    glutIdleFunc(display)
    glutReshapeFunc(redimensionar)
    glutKeyboardFunc(teclado)
    glutSpecialFunc(specialKeys)

    print("Modelos carregados e normalizados:")
    print(f"  A: {len(modelA['vertices'])} vértices, {len(modelA['faces'])} faces")
    print(f"  B: {len(modelB['vertices'])} vértices, {len(modelB['faces'])} faces")
    print("Teclas: m pause/resume | n toggle normals | w/q up/down camera | setas para mover camera | ESC sair")

    glutMainLoop()

if __name__ == '__main__':
    main()
