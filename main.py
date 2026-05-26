from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from datetime import datetime
import os
import uvicorn
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

#os.environ para despliegue. Descomente cuando ya probó todo local.
#Conexion API
client = MongoClient(os.environ["MONGO_URI"])
# TODO: conectarse al cluster Admonsis  

#Host local
#client = MongoClient("")
# TODO: conectarse a la base de datos Admonsis  
db = client["ISIS2304F27202610"]

#Endpoints - accesos
@app.get("/")
def inicio():
    return {"estado": "API funcionando correctamente"}

@app.get("/resenas")
def get_resenas():
    return list(db["resenas"].find({},{"_id":0}))

from datetime import datetime

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


"""
@app.get("/proveedores")
def get_proovedores():
    return list(db["proveedores"].find({},{"_id":0}))

@app.get("/proveedores/{bebida_id}")
def get_proovedor_bebida(bebida_id: int):
    proveedor = db["proveedores"].find_one({"bebidas_suministradas":bebida_id},{"_id":0})
    return proveedor or {}

@app.post("/proveedores")
def post_proveedor(datos:dict):
    datos["fecha_registro"] = datetime.now().isoformat()
    db["proveedores"].insert_one(datos)
    return {"mensaje": "Proveedor registrado"}

@app.put("/proveedores/{nombre}")
def update_proveedor(nombre:str, datos:dict):
    resultado = db["proveedores"].replace_one({"nombre": nombre},datos)
    return {"mensaje":"Proveedor actualizado correctamente"}

@app.patch("/proveedores/{nombre}")
def patch_proveedor(nombre:str, datos:dict):
    resultado = db["proveedores"].update_one({"nombre":nombre},{"$set":datos})
    return {"mensaje":"Campos actualizados correctamente"}

@app.delete("/proveedores/{nombre}")
def delete_proveedor(nombre:str):
    resultado = db["proveedores"].delete_one({"nombre":nombre})
    return {"mensaje":f"Proveedor {nombre} eliminado"}

@app.get("/bares")
def get_bares():
    return list(db["Bares"].find({},{"_id":0}))

@app.get('/bares/{bar_id}')
def get_bar(bar_id: int):
    bares = db["Bares"].find_one({"_id":bar_id},{"_id":0})  # TODO: completar
    return bares or {}

@app.get('/bares/{bar_id}/comentarios')
def get_comentarios(bar_id: int):
    return list(db["comentarios_bares"].find({"bar_id":bar_id},{"_id":0}))

@app.post('/bares/{bar_id}/comentarios')
def post_comentario(bar_id: int, datos: dict):
    datos['bar_id'] = bar_id
    datos['date']  = datetime.now().isoformat()
    # TODO: completar
    db["comentarios_bares"].insert_one(datos)
    return {'mensaje': 'Comentario guardado'}

# TODO: implementar GET /bares/{bar_id}/eventos
# Debe retornar todos los eventos del bar desde la colección 'eventos'

@app.get('/bares/{bar_id}/eventos')
def get_eventos(bar_id:int):
    return list(db["eventos"].find({"bar_id":bar_id}, {"_id":0}))

# TODO: implementar POST /bares/{bar_id}/eventos  
# Debe insertar el evento en la colección 'eventos'
# Recuerde agregar bar_id y fecha_creacion al documento antes de insertar
@app.post("/bares/{bar_id}/eventos")
def post_evento(bar_id:int, datos:dict):
    datos['bar_id'] = bar_id
    datos['fecha_creacion'] = datetime.now().isoformat()
    db["eventos"].insert_one(datos)
    return {"mensaje": "Evento registrado"}
"""