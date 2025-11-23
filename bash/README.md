# Script de Creación de Usuarios - Ejercicio 1

Este script permite crear múltiples usuarios en un sistema Linux a partir de un archivo de configuración.

## Requisitos

- Sistema operativo Linux
- Permisos de superusuario (root) para crear usuarios
- Comandos disponibles: `useradd`, `chpasswd`
- Bash 4.0 o superior

## Formato del archivo de usuarios

El archivo de entrada debe tener el siguiente formato por línea:

```
usuario:comentario:directorio_home:crear_home:shell
```

Donde:
- `usuario`: Nombre del usuario (obligatorio)
- `comentario`: Descripción del usuario (opcional)
- `directorio_home`: Ruta del directorio home (por defecto: /home/usuario)
- `crear_home`: "SI" para crear el directorio home, cualquier otro valor para no crearlo (opcional, por defecto: "NO")
- `shell`: Shell por defecto (opcional, por defecto: /bin/bash)

### Ejemplo de archivo de usuarios (usuarios.txt):

```
juan:Juan Perez:/home/juan:SI:/bin/bash
maria:Maria Garcia::NO:/bin/zsh
pedro:Pedro Lopez:/home/pedro:SI:
```

## Uso

```bash
sudo ./ej1_crea_usuarios.sh [OPCIONES] archivo_usuarios
```

### Opciones:
- `-i`: Modo informativo (muestra detalles de la creación de usuarios)
- `-c CONTRASEÑA`: Establece la contraseña para todos los usuarios creados

### Ejemplos:

1. Crear usuarios sin contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh usuarios.txt
   ```

2. Crear usuarios con contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh -c "P@ssw0rd" usuarios.txt
   ```

3. Ver información detallada de la creación de usuarios:
   ```bash
   sudo ./ej1_crea_usuarios.sh -i usuarios.txt
   ```

4. Combinar modo informativo con contraseña:
   ```bash
   sudo ./ej1_crea_usuarios.sh -i -c "P@ssw0rd" usuarios.txt
   ```


## Códigos de Salida

- `0`: Éxito
- `1`: No se proporcionaron argumentos
- `2`: Falta contraseña después de -c
- `3`: Parámetro desconocido
- `4`: El archivo no existe
- `5`: No es un archivo regular
- `6`: Sin permisos de lectura
- `7`: Formato de línea incorrecto
- `8`: Nombre de usuario vacío

## Pruebas

### 1. Creación básica de usuarios

```bash
# Crear archivo de prueba
echo "usuario1:Usuario de Prueba 1:/home/usuario1:SI:/bin/bash" > test_usuarios.txt
echo "usuario2:Usuario de Prueba 2:/home/usuario2:NO:/bin/sh" >> test_usuarios.txt

# Ejecutar el script
sudo ./ej1_crea_usuarios.sh -i -c "Temp1234" test_usuarios.txt
```

### 2. Verificar usuarios creados

```bash
# Verificar que los usuarios existen
id usuario1
id usuario2

# Verificar directorios home (solo para usuario1)
ls -ld /home/usuario1
ls -ld /home/usuario2  # No debería existir

# Verificar shell
grep usuario1 /etc/passwd
grep usuario2 /etc/passwd
```

## Validaciones de funcionamiento

### 1. Verificación de argumentos

#### a. Sin argumentos

Comando sin argumentos debe mostrar mensaje de error y salir con código 1.

![Sin argumentos](bash/imagenes/comando-sin-arg.png)

#### b. Opción desconocida

Comando con opción desconocida debe mostrar mensaje de error y salir con código 3.

![Argumento desconocido](bash/imagenes/arg-desconocido.png)

#### c. Falta de contraseña después de -c

Comando con -c sin contraseña debe mostrar mensaje de error y salir con código 2.

![Falta contraseña](bash/imagenes/sin-pass.png)

### 2. Verificación de archivo

#### a. Archivo inexistente

Comando con archivo inexistente debe mostrar mensaje de error y salir con código 4.

![Archivo inexistente](bash/imagenes/archivo-inexistente.png)

#### b. Archivo no regular

Comando con archivo que no es regular debe mostrar mensaje de error y salir con código 5.

![Archivo no regular](bash/imagenes/archivo-no-regular.png)

#### c. Sin permisos de lectura

Comando con archivo sin permisos de lectura debe mostrar mensaje de error y salir con código 6.

![Sin permisos](bash/imagenes/sin-permisos.png)

### 3. Validaciones del contenido del archivo

#### a. Línea con formato incorrecto (distinta cantidad de campos)

Comando con línea con formato incorrecto debe mostrar mensaje de error y salir con código 7.

![Formato incorrecto](bash/imagenes/formato-incorrecto.png)

#### b. Nombre de usuario vacío

Comando con nombre de usuario vacío debe mostrar mensaje de error y salir con código 8.

![Nombre vacío](bash/imagenes/nombre-vacio.png)

### 4. Creación correcta de usuarios

#### Configuraciones previas a ejecución del archivo

![Configuraciones previas](bash/imagenes/usuarios-previos-y-archivo.png)

#### Ejecución del comando

![Comando ejecutado](bash/imagenes/ejecucion.png)

- Parametros mapeados correctamente y mostrados a modo de prueba
- Usuarios creados exitosamente y con el modo informativo activo
- Indicación de cantidad de usuarios creados, por tener activo el modo informativo

#### a. Validación de creación de usuarios

Con el comando `getent passwd <usuario>` se confirma que el usuario fue creado mostrando la línea completa de /etc/passwd

![Usuarios creados](bash/imagenes/usuarios-creados.png)

#### b. Verificación HOME creado o no creado

Se verifica que el directorio home se haya creado o no, dependiendo de lo detallado en el archivo de entrada.
Con el comando `ls -ld /home/<usuario>` se verifica la existencia del directorio home.

##### Resultado esperado

| Usuario | Campo HOME  | Campo crear_home | Debe existir |
| ------- | ----------- | ---------------- | ------------ |
| juan    | /home/juan  | SI               | Sí           |
| maria   | /home/maria | NO               | No           |
| pepe    | /home/pepe  | SI               | Sí           |
| lucho   | (vacío)     | NO               | No           |
| ana     | /home/ana   | SI               | Sí           |
| ramiro  | (vacío)     | SI               | Sí           |

##### Resultado

![](bash/imagenes/home.png)

#### c. Verificación SHELL asignada

Se verifica que el shell del usuario se haya asignado correctamente, dependiendo de lo detallado en el archivo de entrada.
Con el comando `getent passwd <usuario> | cut -d: -f7` se muestra solo el shell del usuario.

##### Resultado esperado

| Usuario | Campo SHELL | Debe ser     |
| ------- | ----------- | ------------ |
| juan    | /bin/bash   | /bin/bash    |
| maria   | /bin/sh     | /bin/sh      |
| pepe    | /bin/bash   | /bin/bash    |
| lucho   | (vacío)     | /bin/bash (por defecto)    |
| ana     | /bin/bash   | /bin/zsh     |
| ramiro  | /bin/zsh    | /bin/bash    |

##### Resultado
![Shell asignado](bash/imagenes/shell.png)

#### d. Verificación Comentarios

Se verifica que el comentario del usuario se haya asignado correctamente, dependiendo de lo detallado en el archivo de entrada.
Con el comando `getent passwd <usuario> | cut -d: -f5` se muestra solo el comentario del usuario.

![Comentarios asignados](bash/imagenes/comentario.png)

#### e. Verificación de contraseña

Se verifica que la contraseña se haya asignado correctamente a los usuarios creados.
Con el comando `passwd -S <usuario>` se muestra el estado de la contraseña del usuario.
El primer carácter del estado debe ser P (password set) para indicar que la contraseña está configurada.

![Contraseñas asignadas](bash/imagenes/password.png)

#### f. Verificación de login a un usuario

Se verifica que se pueda iniciar sesión con las contraseñas asignadas.
Con el comando `su - <usuario>` se intenta iniciar sesión como el usuario.

![Login](bash/imagenes/login.png)

#### g. Verificación de re-ejecución (Usuarios ya existen)

Se ejecuta el script nuevamente para verificar que no intente crear usuarios que ya existen.
El script debe mostrar mensajes indicando que los usuarios ya existen y no crear duplicados.

![Re-ejecución](bash/imagenes/re-ejecucion.png)

## Notas

- Se requiere ejecutar el script con privilegios de superusuario (sudo)
- El script verifica si los usuarios ya existen antes de intentar crearlos
- En modo informativo (-i), se muestran mensajes detallados del proceso
- Las contraseñas se aplican a todos los usuarios creados durante la ejecución