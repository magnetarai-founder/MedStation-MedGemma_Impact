"""
Neutron Star Web API
FastAPI backend wrapper for the existing SQL engine
"""

import os
import asyncio
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel, Field
import pandas as pd
import aiofiles
from contextlib import asynccontextmanager
import math
import datetime as _dt

logger = logging.getLogger(__name__)

# Import existing backend modules
import sys
# Insert at the beginning of sys.path to prioritize local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from neutron_core.engine import NeutronEngine, SQLDialect, QueryResult
from redshift_sql_processor import RedshiftSQLProcessor
from sql_validator import SQLValidator
from neutron_utils.sql_utils import SQLProcessor
from neutron_utils.config import config
from neutron_utils.json_utils import df_to_jsonsafe_records as _df_to_jsonsafe_records
from pulsar_core import JsonToExcelEngine

# Session storage
sessions: Dict[str, dict] = {}
query_results: Dict[str, pd.DataFrame] = {}



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Neutron Star API...")
    # Create necessary directories
    api_dir = Path(__file__).parent
    (api_dir / "temp_uploads").mkdir(exist_ok=True)
    (api_dir / "temp_exports").mkdir(exist_ok=True)
    yield
    # Shutdown
    print("Shutting down...")
    for session in sessions.values():
        if 'engine' in session:
            session['engine'].close()

app = FastAPI(
    title="Neutron Star API",
    description="SQL query engine for Excel files",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite/React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include chat router
try:
    from api.chat_service import router as chat_router
    app.include_router(chat_router)
    logger.info("✓ Chat service loaded")
except Exception as e:
    logger.warning(f"Chat service not available: {e}")

# Models
class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime

class ColumnInfo(BaseModel):
    original_name: str
    clean_name: str
    dtype: str
    non_null_count: int
    null_count: int

class FileUploadResponse(BaseModel):
    filename: str
    size_mb: float
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    preview: List[dict]

class QueryRequest(BaseModel):
    sql: str
    limit: Optional[int] = 1000
    dialect: SQLDialect = SQLDialect.DUCKDB
    timeout_seconds: Optional[int] = 300

class QueryResponse(BaseModel):
    query_id: str
    row_count: int
    column_count: int
    columns: List[str]
    execution_time_ms: float
    preview: List[dict]
    has_more: bool

class ExportRequest(BaseModel):
    query_id: str
    format: str = Field(default="excel", pattern="^(excel|csv|parquet|json)$")
    filename: Optional[str] = None

class ValidationRequest(BaseModel):
    sql: str
    dialect: SQLDialect = SQLDialect.DUCKDB

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]

# Helper functions
async def save_upload(upload_file: UploadFile) -> Path:
    """Save uploaded file to temp directory"""
    # Get the directory where this script is located
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / f"{uuid.uuid4()}_{upload_file.filename}"
    # Stream upload to disk in chunks to avoid memory spikes
    chunk_size = 16 * 1024 * 1024  # 16MB
    async with aiofiles.open(file_path, 'wb') as f:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            await f.write(chunk)
    
    return file_path

def get_column_info(df: pd.DataFrame) -> List[ColumnInfo]:
    """Get column information with clean names"""
    from neutron_utils.sql_utils import ColumnNameCleaner
    cleaner = ColumnNameCleaner()
    
    columns: List[ColumnInfo] = []
    for col in df.columns:
        # Use the supported cleaner API (instance method `clean`)
        clean_name = cleaner.clean(str(col))
        columns.append(ColumnInfo(
            original_name=str(col),
            clean_name=clean_name,
            dtype=str(df[col].dtype),
            non_null_count=int(df[col].notna().sum()),
            null_count=int(df[col].isna().sum())
        ))
    return columns

# Endpoints
@app.get("/")
async def root():
    return {"message": "Neutron Star API", "version": "1.0.0"}

@app.post("/sessions/create", response_model=SessionResponse)
async def create_session():
    """Create a new session with isolated engine"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now(),
        "engine": NeutronEngine(),
        "files": {},
        "queries": {}
    }
    return SessionResponse(session_id=session_id, created_at=sessions[session_id]["created_at"])

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Clean up session and its resources"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Close engine
    if 'engine' in session:
        session['engine'].close()
    
    # Clean up temp files
    for file_info in session.get('files', {}).values():
        if 'path' in file_info and Path(file_info['path']).exists():
            Path(file_info['path']).unlink()
    
    # Clean up query results
    for query_id in session.get('queries', {}):
        query_results.pop(query_id, None)
    
    del sessions[session_id]
    return {"message": "Session deleted"}

@app.post("/sessions/{session_id}/upload", response_model=FileUploadResponse)
async def upload_file(session_id: str, file: UploadFile = File(...), sheet_name: Optional[str] = Form(None)):
    """Upload and load an Excel file"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls, .xlsm) and CSV files are supported")
    
    # Save file (streamed) and enforce max size
    file_path = await save_upload(file)
    size_mb = file_path.stat().st_size / (1024 * 1024)
    max_mb = float(config.get("max_file_size_mb", 1000))
    if size_mb > max_mb:
        try:
            file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.1f} MB (limit {int(max_mb)} MB)")
    
    try:
        engine = sessions[session_id]['engine']
        
        # Load into engine based on file type
        lower_name = file.filename.lower()
        if lower_name.endswith('.csv'):
            result = engine.load_csv(file_path, table_name="excel_file")
        else:
            result = engine.load_excel(file_path, table_name="excel_file", sheet_name=sheet_name)

        # Defensive checks in case engine returns unexpected value
        if result is None or not isinstance(result, QueryResult):
            raise HTTPException(status_code=500, detail="Internal error: invalid engine result during load")

        if result.error:
            raise HTTPException(status_code=400, detail=result.error)

        # Get preview data
        preview_result = engine.execute_sql("SELECT * FROM excel_file LIMIT 20")

        if preview_result is None or not isinstance(preview_result, QueryResult):
            raise HTTPException(status_code=500, detail="Internal error: invalid engine result during preview")

        if preview_result.error:
            raise HTTPException(status_code=500, detail=preview_result.error)
        
        # Store file info
        file_info = {
            "filename": file.filename,
            "path": str(file_path),
            "size_mb": file_path.stat().st_size / (1024 * 1024),
            "loaded_at": datetime.now()
        }
        sessions[session_id]['files'][file.filename] = file_info
        
        # Get column info
        columns = get_column_info(preview_result.data)
        
        # JSON-safe preview
        preview_records = _df_to_jsonsafe_records(preview_result.data)

        return FileUploadResponse(
            filename=file.filename,
            size_mb=file_info['size_mb'],
            row_count=result.row_count,
            column_count=len(result.column_names),
            columns=columns,
            preview=preview_records
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/validate", response_model=ValidationResponse)
async def validate_sql(session_id: str, request: ValidationRequest):
    """Validate SQL syntax before execution"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    validator = SQLValidator()
    is_valid, errors, warnings = validator.validate_sql(
        request.sql,
        expected_table="excel_file"
    )
    
    return ValidationResponse(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings
    )

@app.post("/sessions/{session_id}/query", response_model=QueryResponse)
async def execute_query(session_id: str, request: QueryRequest):
    """Execute SQL query"""
    logger.info(f"Executing query for session {session_id}: {request.sql[:100]}...")
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    engine = sessions[session_id]['engine']
    logger.info(f"Engine found for session {session_id}")
    
    # Clean SQL (strip comments/trailing semicolons) to avoid parsing issues when embedding in LIMIT wrapper
    cleaned_sql = SQLProcessor.clean_sql(request.sql)
    logger.info(f"Cleaned SQL: {cleaned_sql[:100]}...")

    # Execute query
    try:
        result = engine.execute_sql(
            cleaned_sql,
            dialect=request.dialect,
            limit=request.limit
        )
        logger.info(f"Query execution completed, rows: {result.row_count if result else 'error'}")
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise
    
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    
    # Store full result for export
    query_id = str(uuid.uuid4())
    query_results[query_id] = result.data
    
    # Store query info
    sessions[session_id]['queries'][query_id] = {
        "sql": request.sql,
        "executed_at": datetime.now(),
        "row_count": result.row_count
    }

    # Return preview (random sample of 100 rows if dataset is large) — JSON-safe
    preview_limit = 100
    if result.row_count > preview_limit:
        # Random sample for better data representation
        preview_df = result.data.sample(n=preview_limit, random_state=None)
    else:
        preview_df = result.data

    preview_data = _df_to_jsonsafe_records(preview_df)

    return QueryResponse(
        query_id=query_id,
        row_count=result.row_count,
        column_count=len(result.column_names),
        columns=result.column_names,
        execution_time_ms=result.execution_time_ms,
        preview=preview_data,
        has_more=result.row_count > preview_limit
    )

@app.post("/sessions/{session_id}/export")
async def export_results(session_id: str, request: ExportRequest):
    """Export query results"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if request.query_id not in query_results:
        raise HTTPException(status_code=404, detail="Query results not found")
    
    df = query_results[request.query_id]
    
    # Generate filename
    filename = request.filename or f"neutron_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Export based on format
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_exports"
    temp_dir.mkdir(exist_ok=True)
    
    if request.format == "excel":
        file_path = temp_dir / f"{filename}.xlsx"
        df.to_excel(file_path, index=False)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif request.format == "csv":
        file_path = temp_dir / f"{filename}.csv"
        df.to_csv(file_path, index=False)
        media_type = "text/csv"
    elif request.format == "parquet":
        file_path = temp_dir / f"{filename}.parquet"
        df.to_parquet(file_path, index=False)
        media_type = "application/octet-stream"
    elif request.format == "json":
        file_path = temp_dir / f"{filename}.json"
        # Convert to JSON-safe records and write with proper formatting
        json_records = _df_to_jsonsafe_records(df)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_records, f, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Invalid export format")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        background=BackgroundTask(lambda: file_path.unlink(missing_ok=True))
    )

@app.get("/sessions/{session_id}/sheet-names")
async def sheet_names(session_id: str, filename: Optional[str] = Query(None)):
    """List Excel sheet names for an uploaded file in this session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        from neutron_utils.excel_ops import ExcelReader
    except Exception:
        raise HTTPException(status_code=500, detail="Excel utilities unavailable")

    files = sessions[session_id].get('files', {})
    file_info = None
    if filename and filename in files:
        file_info = files[filename]
    else:
        # Pick first Excel file in session
        for info in files.values():
            if str(info.get('path', '')).lower().endswith(('.xlsx', '.xls', '.xlsm')):
                file_info = info
                break
    if not file_info:
        raise HTTPException(status_code=404, detail="No Excel file found in session")
    path = Path(file_info['path'])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    try:
        sheets = ExcelReader.get_sheet_names(str(path))
        return {"filename": file_info.get('filename', path.name), "sheets": sheets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/tables")
async def list_tables(session_id: str):
    """List loaded tables in session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    engine = sessions[session_id]['engine']
    tables = []
    
    for table_name, file_path in engine.tables.items():
        table_info = engine.get_table_info(table_name)
        tables.append({
            "name": table_name,
            "file": Path(file_path).name,
            "row_count": table_info.get('row_count', 0),
            "column_count": len(table_info.get('columns', []))
        })
    
    return {"tables": tables}

@app.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time query progress and logs"""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await websocket.accept()
    
    try:
        while True:
            # Receive query request
            data = await websocket.receive_json()
            
            if data.get("type") == "query":
                # Execute query and stream progress
                await websocket.send_json({
                    "type": "progress",
                    "message": "Starting query execution..."
                })
                
                # TODO: Implement actual progress streaming
                # For now, just execute and return result
                engine = sessions[session_id]['engine']
                result = engine.execute_sql(data.get("sql", ""))
                
                if result.error:
                    await websocket.send_json({
                        "type": "error",
                        "message": result.error
                    })
                else:
                    await websocket.send_json({
                        "type": "complete",
                        "row_count": result.row_count,
                        "execution_time_ms": result.execution_time_ms
                    })
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

# JSON to Excel endpoints for Pulsar integration

class JsonUploadResponse(BaseModel):
    filename: str
    size_mb: float
    object_count: int
    depth: int
    columns: List[str]
    preview: List[Dict[str, Any]]

class JsonConvertRequest(BaseModel):
    json_data: str
    options: Dict[str, Any] = Field(default_factory=lambda: {
        "expand_arrays": True,
        "max_depth": 5,
        "auto_safe": True,
        "include_summary": True
    })

class JsonConvertResponse(BaseModel):
    success: bool
    output_file: str
    total_rows: int
    sheets: List[str]
    columns: List[str]
    preview: List[Dict[str, Any]]

@app.post("/sessions/{session_id}/json/upload", response_model=JsonUploadResponse)
async def upload_json(session_id: str, file: UploadFile = File(...)):
    """Upload and analyze JSON file"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    
    # Save uploaded file temporarily
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"
    
    try:
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Analyze JSON structure
        engine = JsonToExcelEngine()
        load_result = engine.load_json(str(file_path))
        
        if not load_result['success']:
            raise HTTPException(status_code=400, detail=load_result.get('error', 'Failed to load JSON'))
        
        # Get column paths
        columns = load_result.get('columns', [])
        
        # Preview data (first 10 objects)
        preview_data = []
        if 'preview' in load_result and hasattr(load_result['preview'], 'to_dict'):
            # Convert DataFrame to list of dicts using JSON-safe conversion
            preview_data = _df_to_jsonsafe_records(load_result['preview'])
        elif 'data' in load_result and isinstance(load_result['data'], list):
            preview_data = load_result['data'][:10]
        
        # Store JSON info in session
        sessions[session_id]['json_file'] = {
            'path': str(file_path),
            'filename': file.filename,
            'engine': engine,
            'columns': columns,
            'data': load_result.get('data', [])
        }
        
        # Get metadata for counts
        metadata = load_result.get('metadata', {})
        data = load_result.get('data', [])
        
        # Calculate object count based on data type
        if isinstance(data, list):
            object_count = len(data)
        elif isinstance(data, dict):
            # Count objects in detected arrays
            detected_arrays = load_result.get('detected_arrays', {})
            if detected_arrays:
                # Use the largest array count
                object_count = max(arr['length'] for arr in detected_arrays.values())
            else:
                object_count = 1
        else:
            object_count = 0
            
        # Estimate depth from column names
        max_depth = 1
        for col in columns:
            depth = col.count('.') + 1
            max_depth = max(max_depth, depth)
        
        return JsonUploadResponse(
            filename=file.filename,
            size_mb=len(content) / (1024 * 1024),
            object_count=object_count,
            depth=max_depth,
            columns=columns[:50],  # Limit columns shown
            preview=preview_data
        )
        
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/json/convert", response_model=JsonConvertResponse)
async def convert_json(session_id: str, request: JsonConvertRequest):
    """Convert JSON data to Excel format"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)

    # Create temporary files
    temp_json = temp_dir / f"{uuid.uuid4()}_input.json"
    temp_excel = temp_dir / f"{uuid.uuid4()}_output.xlsx"

    try:
        # Write JSON data to temp file
        async with aiofiles.open(temp_json, 'w') as f:
            await f.write(request.json_data)

        # Reuse engine from session if available, otherwise create new
        if 'json_file' in sessions[session_id] and 'engine' in sessions[session_id]['json_file']:
            engine = sessions[session_id]['json_file']['engine']
        else:
            engine = JsonToExcelEngine()

        # Check if preview_only mode
        preview_only = request.options.get('preview_only', False)

        if preview_only:
            # Only analyze structure, don't do full conversion
            preview_limit = request.options.get('limit', 100)
            logger.info(f"Analyzing JSON structure for preview (session {session_id}, limit {preview_limit})")

            load_result = engine.load_json(str(temp_json))
            if not load_result['success']:
                raise HTTPException(status_code=400, detail=load_result.get('error', 'Failed to analyze JSON'))

            # Return lightweight preview data with configurable limit
            preview_data = []
            if 'preview' in load_result:
                preview_raw = load_result['preview']
                if hasattr(preview_raw, 'to_dict'):
                    preview_data = _df_to_jsonsafe_records(preview_raw)[:preview_limit]
                elif isinstance(preview_raw, list):
                    preview_data = preview_raw[:preview_limit]
            elif 'data' in load_result and isinstance(load_result['data'], list):
                preview_data = load_result['data'][:preview_limit]

            # Get total rows from metadata or fallback
            total_rows = load_result.get('metadata', {}).get('total_records', len(load_result.get('data', [])))

            result = {
                'success': True,
                'preview_data': preview_data,
                'column_names': load_result.get('columns', []),
                'rows': total_rows,
                'sheet_names': ['Preview'],
                'sheets': 1
            }
            logger.info(f"Preview analysis completed: {result.get('rows', 0)} total rows, {len(preview_data)} in preview")
        else:
            # Full conversion
            logger.info(f"Starting JSON to Excel conversion for session {session_id}")

            result = engine.convert(
                str(temp_json),
                str(temp_excel),
                expand_arrays=request.options.get('expand_arrays', True),
                max_depth=request.options.get('max_depth', 5),
                auto_safe=request.options.get('auto_safe', True),
                include_summary=request.options.get('include_summary', True)
            )

            logger.info(f"Conversion completed with result: {result.get('success', False)}")
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Conversion failed'))
        
        # Store result in session
        sessions[session_id]['json_result'] = {
            'excel_path': str(temp_excel),
            'result': result
        }
        
        # Use preview from result if available, otherwise fallback to reading Excel
        # Random sample for better data representation
        preview_limit = 100
        preview = []
        if 'preview_data' in result and result['preview_data']:
            preview_data = result['preview_data']
            if len(preview_data) > preview_limit:
                # Random sample
                import random
                preview = random.sample(preview_data, preview_limit)
            else:
                preview = preview_data
        elif temp_excel.exists():
            try:
                full_df = pd.read_excel(temp_excel)
                if len(full_df) > preview_limit:
                    preview_df = full_df.sample(n=preview_limit, random_state=None)
                else:
                    preview_df = full_df
                preview = _df_to_jsonsafe_records(preview_df)
            except Exception as e:
                logger.warning(f"Could not read Excel file for preview: {e}")
        
        # Get column information from result first
        column_list = result.get('column_names', [])[:50]
        if not column_list and 'columns' in result:
            if isinstance(result['columns'], list):
                column_list = result['columns'][:50]
            elif isinstance(result['columns'], int) and temp_excel.exists():
                try:
                    df_cols = pd.read_excel(temp_excel, nrows=0)
                    column_list = list(df_cols.columns)[:50]
                except:
                    column_list = []
        
        # Get sheet information
        sheet_names = result.get('sheet_names', [])
        if not sheet_names:
            sheet_count = result.get('sheets', 1)
            if sheet_count > 1:
                sheet_names = [f"Sheet{i+1}" for i in range(sheet_count)]
            else:
                sheet_names = ['Sheet1']

        # Get actual row count from the converted data
        actual_rows = result.get('rows', 0)
        if actual_rows == 0 and len(preview) > 0:
            # Fallback to preview length if engine didn't report row count
            actual_rows = len(preview)

        return JsonConvertResponse(
            success=True,
            output_file=temp_excel.name,
            total_rows=actual_rows,
            sheets=sheet_names,
            columns=column_list,
            preview=preview
        )
        
    except Exception as e:
        # Cleanup temp files
        for f in [temp_json, temp_excel]:
            if f.exists():
                f.unlink()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always cleanup input JSON
        if temp_json.exists():
            temp_json.unlink()

@app.get("/sessions/{session_id}/json/download")
async def download_json_result(session_id: str, format: str = Query("excel", regex="^(excel|csv|tsv|parquet)$")):
    """Download converted JSON as Excel or CSV"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if 'json_result' not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="No conversion result found")
    
    excel_path = Path(sessions[session_id]['json_result']['excel_path'])
    
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    if format == "excel":
        return FileResponse(
            excel_path,
            filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # Convert to other formats
        try:
            df = pd.read_excel(excel_path, sheet_name=0)
            
            if format == "csv":
                output_path = excel_path.with_suffix('.csv')
                df.to_csv(output_path, index=False)
                media_type = "text/csv"
                extension = "csv"
            elif format == "tsv":
                output_path = excel_path.with_suffix('.tsv')
                df.to_csv(output_path, index=False, sep='\t')
                media_type = "text/tab-separated-values"
                extension = "tsv"
            elif format == "parquet":
                output_path = excel_path.with_suffix('.parquet')
                df.to_parquet(output_path, index=False)
                media_type = "application/octet-stream"
                extension = "parquet"
            
            return FileResponse(
                output_path,
                filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}",
                media_type=media_type,
                background=BackgroundTask(lambda: output_path.unlink() if output_path.exists() else None)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{format.upper()} conversion failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
