#!/bin/bash

#Inizialización
modo_info=false
password=""
#Obtener el total de parametros
total_params=$#
#Obtener el archivo (ultimo parametro)
archivo="${!total_params}"

#Validar que haya al menos un parametro
if [ $# -eq 0 ]; then
    echo "Error: No se proporciono ningun argumento, se necesitan al menos el archivo que contenga los usuarios" >&2
    exit 1
fi

#Validación primer parametro
if [ "$1" = "-i" ]; then
    modo_info=true
elif [ "$1" = "-c" ]; then
    #Validación que contraseña no sea vacía
    if [ -z "$2" ]; then
        echo "Error: Falta la contraseña después de -c." >&2
        exit 2
    fi
    password="$2"
else
    archivo="$1"
fi

# Validación segundo parámetro (si existe)
if [ "$2" = "-c" ]; then
    #Validación que contraseña no sea vacía
    if [ -z "$3" ]; then
        echo "Error: Falta la contraseña después de -c." >&2
        exit 3
    fi
    password="$3"
fi

