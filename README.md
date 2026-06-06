# AgroNest API

Backend de la plataforma **AgroNest** — DeFi agrícola sobre Ethereum/Sepolia. Permite registrar cosechas como NFTs, gestionar inversiones tokenizadas, operar bóvedas de rendimiento y conectar con CETES on-chain a través de Etherfuse.

## Stack

| Capa | Tecnología |
|---|---|
| Framework | FastAPI 0.111 |
| ORM | Tortoise ORM 0.21 + asyncpg |
| Base de datos | PostgreSQL 14+ |
| Caché / sesiones | Redis 5 (opcional — degradación elegante) |
| Autenticación | JWT (PyJWT 2.8) — access + refresh tokens |
| Blockchain | web3.py 7 — red Sepolia (chain ID 11155111) |
| AI | Google Gemini (google-genai) con fallback sin credenciales |
| CETES on-chain | Etherfuse (modo mock cuando API key está vacía) |
| Marketplace NFT | Rare Protocol / SuperRare (Base Sepolia) |
| Config | pydantic-settings (`.env`) |
| Servidor | uvicorn 0.30 |

---

## Requisitos previos

- Python 3.11+
- PostgreSQL corriendo en `localhost:5432`
- (Opcional) Redis corriendo en `localhost:6379`

---

## Instalación

```bash
cd Argos-Net-Api

# Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración

Copia `.env.example` a `.env` (o edita `.env` directamente). Todas las variables son obligatorias:

```env
# API
API_BASE_URL=http://localhost:8001
API_BASE_DESCRIPTION="Entorno Local"
ENVIRONMENT_BASE_URL='{"LOCAL": "http://localhost:8001/"}'

# Swagger Basic Auth
SWAGGER_USERNAME=<usuario-swagger>
SWAGGER_PASSWORD=<contraseña-swagger>
SKIP_SETUP=False
SECRET_KEY=<cadena-aleatoria-secreta>

# JWT
JWT_SECRET=<hex-64-chars>
JWT_SECRET_RENEW=<hex-64-chars>
JWT_TOKEN_EXPIRATION=200       # minutos
JWT_RENEW_EXPIRATION=9         # minutos
ALGORITHM=HS256

# Logs
LOG_ROUTE=log/
LOG_LEVEL=DEBUG
LOG_FILE_SIZE=21600000
LOG_BACKUP_COUNT=30
LOG_NOMENCLATURE=log

# Base de datos
DB_SERVER=localhost
DB_SERVER_PORT=5432
DB_USER=<usuario-postgres>
DB_PASSWORD=<contraseña-postgres>
DB_DATABASE=<nombre-base-de-datos>

# Redis (opcional — la API funciona sin él)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_EXP=86400

# SMTP (recuperación de contraseña)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<correo>
SMTP_PASSWORD=<app-password>
VCODE_EXP_MIN=3
ML_EXP_MIN=30

CREATE_CONFIGURATION=True

# Blockchain (Sepolia)
RPC_URL=https://sepolia.drpc.org
CHAIN_ID=11155111
API_PRIVATE_KEY=<clave-privada-dev>      # NUNCA en producción
CONTRACT_ABI_DIR=./contracts/abis
AGRONEST_CONTRACT_ADDRESS=<address>
USDC_CONTRACT_ADDRESS=<address>

# Google Gemini AI (dejar vacío activa respuestas demo)
GEMINI_API_KEY=

# Etherfuse CETES (dejar vacío activa modo mock con datos demo)
ETHERFUSE_API_KEY=
ETHERFUSE_BASE_URL=https://api.sand.etherfuse.com

# Rare Protocol / NFT Marketplace
RARE_CONTRACT_ADDRESS=
RARE_NETWORK=base-sepolia
```

---

## Migración de base de datos

Antes del primer arranque, ejecuta el script de migración para añadir las columnas nuevas:

```bash
psql -U postgres -d posbase -f scripts/migrate_v2.sql
```

Contenido del script:
```sql
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS wallet_address VARCHAR(42);
ALTER TABLE cosechas ADD COLUMN IF NOT EXISTS latitud FLOAT;
ALTER TABLE cosechas ADD COLUMN IF NOT EXISTS longitud FLOAT;
```

---

## Arranque

```bash
# Desarrollo (recarga automática)
uvicorn main:app --host 127.0.0.1 --port 8001 --reload

# Producción
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

La API queda disponible en `http://localhost:8001`.

---

## Documentación interactiva

| URL | Descripción |
|---|---|
| `http://localhost:8001/docs` | Swagger UI (requiere Basic Auth) |
| `http://localhost:8001/redoc` | ReDoc |
| `http://localhost:8001/openapi.json` | Esquema OpenAPI |

Credenciales Swagger: `SWAGGER_USERNAME` / `SWAGGER_PASSWORD` del `.env`.

---

## Endpoints

### Autenticación — `/token`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/token` | Login — devuelve `access_token` y `refresh_token` (form-urlencoded) |
| POST | `/token/renovacion` | Renueva el access token usando el refresh token |
| POST | `/token/revocacion` | Revoca (logout) el token activo |

### Usuarios — `/usuarios`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/usuarios` | Registro de nuevo usuario |
| GET | `/usuarios/mi_info` | Perfil del usuario autenticado |
| PUT | `/usuarios/{id}` | Editar perfil |

### Cosechas — `/cosechas`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/cosechas` | Registrar cosecha y mintear NFT en Sepolia |
| GET | `/cosechas` | Listar todas las cosechas (paginado) |
| GET | `/cosechas/mis_cosechas` | Cosechas del usuario autenticado |
| GET | `/cosechas/{id}` | Detalle de una cosecha |
| POST | `/cosechas/{id}/eliminar` | Eliminar cosecha (soft delete) |

### Bóveda — `/boveda`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/boveda` | Abrir bóveda para una cosecha |
| GET | `/boveda` | Listar bóvedas (filtro por estado) |
| GET | `/boveda/{id}` | Detalle de bóveda |
| GET | `/boveda/cosecha/{cosecha_id}` | Bóveda por cosecha |
| GET | `/boveda/{id}/chain` | Estado on-chain de la bóveda |

### Inversiones — `/inversiones`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/inversiones` | Crear inversión en una cosecha |
| GET | `/inversiones` | Mis inversiones |
| GET | `/inversiones/{id}` | Detalle de inversión |

### Blockchain — `/blockchain`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/blockchain/wallet` | Dirección y balances del wallet custodial |
| GET | `/blockchain/balance/{address}` | Balances ETH + USDC + bCROP de cualquier address |
| GET | `/blockchain/tx/{tx_hash}` | Estado de una transacción |

### Etherfuse CETES — `/etherfuse`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/etherfuse/onboarding` | KYC — crea cliente Etherfuse |
| GET | `/etherfuse/customer` | Datos del cliente KYC |
| PUT | `/etherfuse/customer/wallet` | Actualizar wallet address |
| GET | `/etherfuse/assets` | Activos CETES disponibles |
| POST | `/etherfuse/quote` | Cotizar onramp / offramp |
| POST | `/etherfuse/order` | Crear orden de conversión |
| POST | `/etherfuse/order/{id}/simulate` | Simular recepción de fiat (sandbox) |
| GET | `/etherfuse/orders` | Historial de órdenes |
| GET | `/etherfuse/orders/{id}` | Detalle de orden |
| POST | `/etherfuse/webhook` | Webhook para eventos de Etherfuse |

> **Modo mock:** cuando `ETHERFUSE_API_KEY` está vacía, todos los endpoints devuelven datos demo realistas sin llamar a la API real.

### Marketplace NFT — `/marketplace`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/marketplace` | Listar NFTs en venta |
| GET | `/marketplace/{id}` | Detalle de listing |
| POST | `/marketplace` | Publicar NFT de cosecha |
| PUT | `/marketplace/{id}/confirm` | Confirmar listing on-chain |
| POST | `/marketplace/{id}/cancel` | Cancelar listing |
| POST | `/marketplace/{id}/sold` | Marcar como vendido |

### Oracle / Satélite — `/oracle`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/oracle/ndvi` | Índice de vegetación NDVI por coordenadas |

### AI Chat — `/ai`

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/ai/chat` | Chat con asistente agrícola (Gemini) |

---

## Estructura del proyecto

```
Argos-Net-Api/
├── App/
│   ├── core/
│   │   └── settings.py          # Configuración desde .env (pydantic-settings)
│   ├── models/                  # Modelos Tortoise ORM
│   │   ├── usuario.py
│   │   ├── cosecha.py
│   │   ├── inversion.py
│   │   ├── boveda.py
│   │   ├── etherfuse_cliente.py
│   │   ├── etherfuse_orden.py
│   │   └── nft_listing.py
│   ├── routers/                 # Rutas FastAPI
│   ├── schemas/                 # Modelos Pydantic (validación I/O)
│   ├── services/                # Lógica de negocio
│   │   ├── cosechas.py          # Mint NFT + persistencia
│   │   ├── etherfuse.py         # CETES on-chain (con modo mock)
│   │   ├── blockchain.py        # Consultas web3
│   │   ├── rare_protocol.py     # Marketplace NFT
│   │   └── web3_client.py       # Cliente web3 singleton
│   ├── utils/
│   │   ├── auth.py              # JWT, get_current_user, tokenOut
│   │   └── logger.py            # Logger configurable
│   └── setup/
│       └── setup.py             # Datos iniciales (roles, endpoints)
├── contracts/
│   └── abis/                    # ABIs de contratos inteligentes
├── scripts/
│   └── migrate_v2.sql           # Migraciones manuales
├── log/                         # Archivos de log (generados en runtime)
├── main.py                      # Entry point FastAPI
├── requirements.txt
└── .env                         # Variables de entorno (no commitear)
```

---

## Notas de desarrollo

- **Redis no requerido:** la API opera sin Redis. La revocación de tokens y el control de sesión única se saltan silenciosamente con un warning en log; los tokens expiran por TTL del JWT.
- **Blockchain Sepolia:** el mint de NFTs requiere ETH de testnet en `API_PRIVATE_KEY`. Obtener en https://sepoliafaucet.com.
- **Gemini AI:** sin API key, el chat responde con datos demo. Obtener key en https://aistudio.google.com.
- **Etherfuse:** sin API key, todos los endpoints CETES devuelven datos mock. Obtener key en https://dashboard.etherfuse.com.
