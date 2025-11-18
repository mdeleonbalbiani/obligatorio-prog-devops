#!/bin/bash

# Inicialización de variables
modo_info=false     # Indica si se usa la opción -i
password=""         # Guarda la contraseña si se usa -c

# Validación: debe haber al menos 1 parámetro
if [ $# -eq 0 ]; then
    echo "Error: No se proporciono ningun argumento, se necesitan al menos el archivo que contenga los usuarios" >&2
    exit 1
fi

# El último parámetro siempre se considera el archivo
# Ejemplo: ./ej1_crea_usuarios.sh -i -c hola usuarios.txt
# El archivo es el "usuarios.txt"
total=$#                   # Cantidad total de parámetros
archivo="${!total}"        # Parámetro número $total = archivo

# Procesar los parámetros excepto el último
# porque el último es el archivo y no una opción
i=1  # contador para recorrer los parámetros

while [ $i -lt $total ]; do
    # ${!i} = expansión indirecta, toma el parámetro número i (si i=2, esto es $2)
    param="${!i}"   # obtiene el parámetro actual (ej: $1, $2, ...)

    case "$param" in

        # Opción -i = activar modo informativo
        -i)
            modo_info=true
            ;;

        # Opción -c = la contraseña es el siguiente parámetro
        -c)
            next=$((i+1))  # siguiente parámetro

            # Si el siguiente parámetro es el archivo significa que no dieron contraseña
            if [ $next -eq $total ]; then
                echo "Error: falta la contraseña después de -c." >&2
                exit 2
            fi

            # Guardamos la contraseña que está en el siguiente parámetro
            # ${!next} obtiene el parámetro donde está la contraseña (por ejemplo $3 o $4)
            password="${!next}"

            # Saltamos ese parámetro extra
            i=$((i+1))
            ;;

        # Cualquier otro texto antes del archivo → error
        *)
            echo "Error: parámetro desconocido: $param" >&2
            exit 3
            ;;
    esac

    i=$((i+1))  # pasar al siguiente parámetro
done

# Mostrar los resultados (solo para pruebas)
echo "----- Resultados de los paramentros ----"
echo "-------- (solo para pruebas) -----------"
echo "Modo informativo: $modo_info"
echo "Contraseña: ${password:+(proporcionada)}"
echo "Archivo: $archivo"
echo "---------------------------------------"

# --- Validación del archivo ---
# Verificar que el archivo existe
if [ ! -e "$archivo" ]; then
    echo "Error: El archivo '$archivo' no existe." >&2
    exit 4
fi

# Verificar que es un archivo regular (no un directorio)
if [ ! -f "$archivo" ]; then
    echo "Error: '$archivo' no es un archivo regular." >&2
    exit 5
fi

# Verificar permisos de lectura
if [ ! -r "$archivo" ]; then
    echo "Error: No se tienen permisos de lectura sobre '$archivo'." >&2
    exit 6
fi

# --- Procesamiento del archivo ---

# Contador de usuarios creados con éxito
exito=0

# Leer el archivo línea por línea
while IFS= read -r linea; do

    # Saltar líneas vacías
    [ -z "$linea" ] && continue

    # Separar campos
    user=$(echo "$linea" | cut -d ":" -f1)
    comment=$(echo "$linea" | cut -d ":" -f2)
    home=$(echo "$linea" | cut -d ":" -f3)
    crear_home=$(echo "$linea" | cut -d ":" -f4)
    shell=$(echo "$linea" | cut -d ":" -f5)

    # Validar que haya exactamente 5 campos
    total_campos=$(echo "$linea" | awk -F":" '{print NF}')
    if [ "$total_campos" -ne 5 ]; then
        echo "Error: línea '$linea' con formato incorrecto" >&2
        exit 7
    fi

    # Nombre de usuario no puede estar vacío
    if [ -z "$user" ]; then
        echo "Error: nombre de usuario vacío en línea '$linea'" >&2
        exit 8
    fi

    # Valores por defecto si el campo está vacío
    [ -z "$comment" ] && comment=""
    [ -z "$home" ] && home="/home/$user"
    [ -z "$crear_home" ] && crear_home="NO"
    [ -z "$shell" ] && shell="/bin/bash"

    # Inicializamos variable
    cmd=(useradd)

    # Crear o no crear directorio home
    if [ "$crear_home" = "NO" ]; then
        cmd+=(-M)   # NO crear home
    else
        cmd+=(-m)   # Crear home
    fi

    # Parámetros obligatorios
    cmd+=(-d "$home")
    cmd+=(-s "$shell")
    cmd+=(-c "$comment")

    # Nombre del usuario al final
    cmd+=("$user")

    # ----- Ejecutar el comando useradd -----
    "${cmd[@]}"
    resultado=$?

    # ----- Procesar resultados -----

    if [ $resultado -eq 0 ]; then
        exito=$((exito+1))

        if $modo_info; then
            echo "Usuario $user creado con éxito con datos indicados:"
            echo "Comentario: ${comment:-<valor por defecto>}"
            echo "Dir home: $home"
            echo "Asegurado existencia de directorio home: $crear_home"
            echo "Shell por defecto: $shell"
            echo
        fi

        # Si hay contraseña, setearla
        if [ -n "$password" ]; then
            echo "$user:$password" | chpasswd
        fi

    else
        if $modo_info; then
            echo "ATENCION: el usuario $user no pudo ser creado"
            echo
        fi
    fi

done < "$archivo"

# Al final, mostrar total si se pidió -i
if $modo_info; then
    echo "Se han creado $exito usuarios con éxito."
fi


