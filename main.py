from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import uvicorn
from datetime import datetime
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

#os.environ para despliegue. Descomente cuando ya probó todo local.
#Conexion API
# client = MongoClient(os.environ["MONGO_URI"])
# TODO: conectarse al cluster Admonsis  

#Host local
client = MongoClient("mongodb://ISIS2304F27202610:Y5X4Ku2ekSCh@157.253.236.88:8087")
# TODO: conectarse a la base de datos Admonsis  
db = client["ISIS2304F27202610"]

#Endpoints - accesos
@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

@app.get("/resenas")
def get_resenas():
    return list(db["resenas"].find({},{"_id":0}))

@app.get("/top-10/{inicio}/{fin}")
def get_top_10(inicio: datetime,fin: datetime):
    pipeline = [{"$match": {
                "fecha_creacion": {
                    "$gte": inicio,
                    "$lte": fin
                }
            }
        },
        {
            "$group": {
                "_id": "$id_hotel",
                "promedio": {"$avg": "$calificacion"}}
        },
        {
            "$limit": 10
        }
    ]
    return list( db["resenas"].aggregate(pipeline))

@app.get("/reputacion/{hotel_id}/{anio}")
def reputacion(hotel_id:int,anio:int):
    pipeline = [
    {
     "$match": {
        "$expr": {
          "$eq": [
            { "$year": '$fecha_creacion' },
            anio
          ]
        },
        "id_hotel": hotel_id
      }
    },
    {
      "$group": {
        "_id": {
          "mes": { "$month": '$fecha_creacion' }
        },
        "promedio": { "$avg": '$calificacion' }
      }
    },
    {
      "$project": {
        "_id": 0,
        "mes": '$_id.mes',
        "promedio": { "$round": ["$promedio", 2] }
      }
    },
    { "$sort": { "mes": 1 } }
]
    return list( db["resenas"].aggregate(pipeline))

@app.get("/comparacion/{ciudad}/{pais}")
def comparacion(ciudad:str, pais:str):
    pipeline = [
    {
      "$match": {
        "ciudad": {
          "nombre": ciudad,
          "pais": pais
        }
      }
    },
    {
      "$group": {
        "_id": '$id_hotel',
        "calificacion_promedio": {
          "$avg": '$calificacion'
        },
        "total_resenas": { "$count": {} },
        "porcentaje_destacadas": {
          "$avg": { "$cond": ['$destacada', 100, 0] }
        },
        "porcentaje_respuesta": {
          "$avg": {
            "$cond": [
              '$respuesta_administrador',
              100,
              0
            ]
          }
        }
      }
    },
    {
      "$project": {
        "_id": 1,
        "calificacion_promedio": {
          "$round": ["$calificacion_promedio", 2]
        },
        "total_resenas": 1,
        "porcentaje_destacadas": {
          "$round": ["$porcentaje_destacadas", 2]
        },
        "porcentaje_respuesta": {
          "$round": ["$porcentaje_respuesta", 2]
        }
      }
    }
  
]
    return list( db["resenas"].aggregate(pipeline))

@app.get("/resenas/{codigo_res}")
def get_resena(codigo_res: int):
    resena = db["resenas"].find_one(
        {"codigo_confirmacion": codigo_res},
        {"_id": 0}
    )
    if not resena:
        return {"error": "Reseña no encontrada"}
    return resena

# Inserciones

"""
Cada reseña es dependiente del código de confirmación de una reserva.
Es decir que solo hay una reseña por cada reserva en el sistema.

Datos que da el usuario:
calificacion, comentario

Resto de datos que se autocompletan por detrás en apex:
id_hotel, nombre_hotel, ciudad y pais, correo, votos, destacada

Opcional: respuesta_administrador.

Constantes del javascript:
ciudad, pais, hotel_id, correo, nombre_hotel, codigo_confirmacion
Asumimos que estas constantes ya se encuentran en el diccionario datos.
"""
#RF1 - Crear reseña
@app.post("/resenas/{codigo_res}")
def post_resenas(codigo_res:int, datos:dict):
    existente = db["resenas"].find_one({"codigo_confirmacion": codigo_res})
    if existente:
        return {"error":"La reserva ya tiene una reseña"}
    
    datos["codigo_confirmacion"] = codigo_res
    datos["fecha_creacion"] = datetime.now()
    datos["votos"] = 0
    datos["destacada"] = False
    datos["votos_resena"] = []
    datos["estado"] = "Publicada"
    #el id de la reseña se asigna automaticamente al generar la insercion
    db["resenas"].insert_one(datos)
    return {"mensaje": "Reseña registrada correctamente"}

#RF2 - Editar reseña
#El usuario solo podrá modificar el comentario que realiza o la calificación del hotel
@app.patch("/resena/{codigo_res}")
def patch_resena(codigo_res:int, datos:dict):
    resultado = db["resenas"].update_one({"codigo_confirmacion":codigo_res},{"$set":datos})
    return {"mensaje":"Campos de reseña actualizados correctamente"}

#RF3 y RF8 - Eliminar reseña (accesible tanto para cliente como para admin)
@app.patch("/resena/{codigo_res}/eliminar")
def delete_resena(codigo_res:int):
    resultado = db["resenas"].update_one({"codigo_confirmacion":codigo_res}, {"$set":{"estado":"Eliminada"}})
    return {"mensaje":f"Reseña del número de reserva {codigo_res} ha sido eliminada"}

#RF4 - Consultar reseñas de un hotel
#De esta consulta se puede hacer o proyección de los datos o desde apex solo tomar los campos pertinentes.
@app.get("/resenas/hotel/{id_hotel}")
def get_resenas_hotel(id_hotel:int):
    return list(db["resenas"].find({"id_hotel":id_hotel},{"_id":0}))
  
  
  
#RF9 - Destacar reseña
@app.patch("/resenas/destacar/{codigo_res}")
def destacar_resena(codigo_res:int):
    resultado = db["resenas"].update_one({"codigo_confirmacion":codigo_res}, {"$set":{"destacada":True}})
    return {"mensaje":f"Reseña {codigo_res} marcada como destacada"}
  
  
#RF5 - Marcar reseña como útil
@app.patch("/resenas/{codigo_res}/{correo}")
def marcar_resena_util(codigo_res:int, correo:str):
    resena = db["resenas"].find_one({"codigo_confirmacion":codigo_res}, {"_id":0})
    if not resena:
        return {"error": "Reseña no encontrada"}

    if correo in resena.get("votos_resena", []):
        db["resenas"].update_one(
            {"codigo_confirmacion":codigo_res},
            {
                "$pull": {"votos_resena": correo},
                "$inc": {"votos": -1}
            }
        )
        return {"mensaje":f"Reseña ya no está marcada para {correo}"}
    
    else:
        db["resenas"].update_one(
            {"codigo_confirmacion":codigo_res},
            {
                "$push": {"votos_resena": correo},
                "$inc": {"votos": 1}
            }
        )
        return {"mensaje":f"Reseña marcada como útil por {correo}"}
    
#RF6 - Consultar historial de reseñas propias
@app.get("/resenas/usuario/{correo}")
def historial_resenas(correo:str):
    return list(db["resenas"].find({"correo_cliente":correo},{"_id":0, "estado":1, "calificacion":1, "respuesta_administrador":1, "votos":1, "fecha_creacion":1, "id_hotel":1, "nombre_hotel":1, "codigo_confirmacion":1}))
 
#RF7 - Responder reseña (agregar o editar)
#Los datos que recibe este patch tienen que ser de la forma {"respuesta_administrador":comentario}
@app.patch("/resenas/{codigo_res}/respuesta")
def responder_resena(codigo_res:int, datos:dict):
    resultado = db["resenas"].update_one({"codigo_confirmacion":codigo_res}, {"$set":{"respuesta_administrador":datos["respuesta_administrador"]}})
    return {"mensaje":f"Respuesta del hotel del número de reserva {codigo_res} añadida"}


