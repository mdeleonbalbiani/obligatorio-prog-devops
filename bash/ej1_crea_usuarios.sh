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

#Validación primer parametro
if [ $1 = "-i" ]; then
    modo_info=true
else
    if [ $1 = "-c" ]; then
        password=$2
    else
        archivo=$1
    fi 
fi

