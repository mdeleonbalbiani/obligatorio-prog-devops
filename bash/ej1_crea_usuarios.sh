#!/bin/bash

#Inizialización
modo_info=false
password=""
archivo=""

#Validar que haya al menos un parametro
if [ $# -eq 0 ]; then
    echo "Error: No se proporciono ningun argumento, se necesitan al menos el archivo que contenga los usuarios" 2>&1
    exit 1
fi
