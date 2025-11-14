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
echo "Modo informativo: $modo_info"
echo "Contraseña: ${password:+(proporcionada)}"
echo "Archivo: $archivo"
