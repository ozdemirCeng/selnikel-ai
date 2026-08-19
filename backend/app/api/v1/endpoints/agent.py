import io
import json
import time
from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.logging import logger
from app.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    PDFReportRequest,
    ToolDefinitionSchema,
)
from app.services.agent.orchestrator import engineering_agent
from app.services.reporting import (
    EngineeringExcelExporter,
    EngineeringPDFExporter,
    EngineeringPowerPointExporter,
    EngineeringWordExporter,
)

router = APIRouter(prefix="/agent", tags=["AI Engineering Agent"])


@router.get(
    "/tools",
    response_model=List[ToolDefinitionSchema],
    summary="List available engineering tools",
)
async def list_tools():
    """Returns definitions and parameter schemas for all available engineering tools."""
    tool_defs = engineering_agent.get_tool_definitions()
    return [t.model_dump() for t in tool_defs]


@router.post(
    "/run",
    response_model=AgentRunResponse,
    summary="Execute multi-step engineering agent synchronously",
)
async def run_agent(request: AgentRunRequest):
    """Executes multi-step reasoning, tool invocations, and answer synthesis."""
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query cannot be empty.",
        )

    try:
        response = await engineering_agent.run(
            query=request.query,
            max_steps=request.max_steps,
        )
        return response
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.post(
    "/stream",
    summary="Stream real-time agent thoughts, tool calls, and final answer via SSE",
)
async def stream_agent(request: AgentRunRequest):
    """Streams SSE events as the agent reasons, executes tools, and produces the final answer."""
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query cannot be empty.",
        )

    async def event_generator():
        try:
            # Emit start event
            yield f"data: {json.dumps({'type': 'start', 'query': request.query})}\n\n"

            # Execute run
            response = await engineering_agent.run(
                query=request.query,
                max_steps=request.max_steps,
            )

            # Stream each reasoning step
            for step in response.steps:
                yield f"data: {json.dumps({'type': 'step', 'step': step.model_dump()}, ensure_ascii=False)}\n\n"

            # Stream final answer
            yield f"data: {json.dumps({'type': 'final_answer', 'answer': response.final_answer, 'tools_used': response.tools_used, 'latency_ms': response.total_execution_time_ms}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/report/pdf",
    summary="Export technical markdown report to styled PDF document",
)
async def export_pdf_report(request: PDFReportRequest):
    """Generates a high-fidelity PDF from the provided markdown content."""
    if not request.markdown_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Markdown content cannot be empty.",
        )

    try:
        pdf_bytes = EngineeringPDFExporter.generate_pdf(
            markdown_text=request.markdown_content,
            title=request.title or "Selnikel Teknik Raporu",
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="Selnikel_Teknik_Raporu_{int(time.time())}.pdf"',
            },
        )
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        )


@router.post(
    "/report/excel",
    summary="Export engineering calculations & tables to formatted Excel spreadsheet (.xlsx)",
)
async def export_excel_report(request: PDFReportRequest):
    """Generates a formatted Microsoft Excel spreadsheet (.xlsx) from markdown tables and calculations."""
    if not request.markdown_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Markdown content cannot be empty.",
        )

    try:
        excel_bytes = EngineeringExcelExporter.generate_excel(
            markdown_text=request.markdown_content,
            title=request.title or "Selnikel Mühendislik Verileri",
        )

        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="Selnikel_Hesaplama_{int(time.time())}.xlsx"',
            },
        )
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Excel: {str(e)}",
        )


@router.post(
    "/report/word",
    summary="Export technical markdown report to formal Microsoft Word document (.docx)",
)
async def export_word_report(request: PDFReportRequest):
    """Generates a formal Microsoft Word document (.docx) with Selnikel headers and tables."""
    if not request.markdown_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Markdown content cannot be empty.",
        )

    try:
        docx_bytes = EngineeringWordExporter.generate_docx(
            markdown_text=request.markdown_content,
            title=request.title or "Selnikel Teknik Raporu",
        )

        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="Selnikel_Rapor_{int(time.time())}.docx"',
            },
        )
    except Exception as e:
        logger.error(f"Word export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Word document: {str(e)}",
        )


@router.post(
    "/report/powerpoint",
    summary="Export technical briefing to widescreen PowerPoint presentation (.pptx)",
)
async def export_powerpoint_report(request: PDFReportRequest):
    """Generates a widescreen 16:9 Microsoft PowerPoint presentation (.pptx) from markdown text."""
    if not request.markdown_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Markdown content cannot be empty.",
        )

    try:
        pptx_bytes = EngineeringPowerPointExporter.generate_pptx(
            markdown_text=request.markdown_content,
            title=request.title or "Selnikel Mühendislik Sunumu",
        )

        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f'attachment; filename="Selnikel_Sunum_{int(time.time())}.pptx"',
            },
        )
    except Exception as e:
        logger.error(f"PowerPoint export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PowerPoint: {str(e)}",
        )


