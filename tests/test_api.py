"""Every endpoint and every error code, with a fake LLM (no API cost) and search switched off."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import Server.ingestion.upload_store as upload_store
from AI.errors import AIRateLimitedError, AIUnavailableError
from Server.main import create_app
from tests.fake_llm import FakeLLM, call, tool_reply

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_docs"
ABOVE_MILLION = {"filters": [{"column": "amount", "operator": ">", "value": 1000000}]}


@pytest.fixture
def client():
    app = create_app(load_docs_folder=False)
    app.state.lens.use_search = False
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def loaded(client):
    assert client.post("/api/documents/load", json={"folder_path": str(SAMPLE_DIR)}).status_code == 200
    return client


def error_code(response) -> str:
    return response.json()["error"]["code"]


def test_health_reports_model_and_document_count(loaded):
    body = loaded.get("/api/health").json()
    assert body["status"] == "ok" and body["documents_loaded"] == 6 and body["model"]


def test_load_folder_returns_every_status_and_skipped_files(client):
    body = client.post("/api/documents/load", json={"folder_path": f'"{SAMPLE_DIR}"'}).json()  # quotes are ok
    statuses = {document["name"]: document["status"] for document in body["documents"]}
    assert statuses["Corrupt_Report.pdf"] == "corrupt" and statuses["Protected_Annex.pdf"] == "encrypted"
    assert body["readable_count"] == 6
    assert body["skipped"] == [{"name": "Meeting_Notes.docx", "reason": "Unsupported file type (.docx)"}]
    boq = next(d for d in body["documents"] if d["name"] == "BOQ_Phase1.xlsx")
    assert boq["tables"][0]["rows"] == 18 and "Total Amount (SAR)" in boq["tables"][0]["columns"]
    assert client.get("/api/documents").json()["documents"] == body["documents"]


def test_missing_folder_is_folder_not_found(client):
    response = client.post("/api/documents/load", json={"folder_path": str(SAMPLE_DIR / "nope")})
    assert response.status_code == 404 and error_code(response) == "FOLDER_NOT_FOUND"


def test_folder_without_pdf_or_excel_is_folder_empty(client, tmp_path):
    (tmp_path / "notes.txt").write_text("hello")
    response = client.post("/api/documents/load", json={"folder_path": str(tmp_path)})
    assert (
        error_code(response) == "FOLDER_EMPTY" and "1 other files were skipped" in response.json()["error"]["message"]
    )


def test_chat_before_loading_is_no_documents_loaded(client):
    response = client.post("/api/chat", json={"question": "hi"})
    assert response.status_code == 409 and error_code(response) == "NO_DOCUMENTS_LOADED"


@pytest.mark.parametrize("body", [{"question": "   "}, {"question": "x", "history": [{"role": "bot", "content": "x"}]}])
def test_bad_chat_request_is_invalid_request(loaded, body):
    response = loaded.post("/api/chat", json=body)
    assert response.status_code == 422 and error_code(response) == "INVALID_REQUEST"


def test_chat_returns_answer_table_sources_and_steps(loaded):
    submit = {"answer": "Found **18** items.", "table_result_id": "t1",
              "sources": [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ"}]}  # fmt: skip
    loaded.app.state.lens.llm = FakeLLM(
        [tool_reply(call("query_table", ABOVE_MILLION)), tool_reply(call("submit_answer", submit))]
    )
    body = loaded.post("/api/chat", json={"question": "Items above SAR 1M", "history": []}).json()
    assert body["answer"] == "Found **18** items."
    assert len(body["table"]["rows"]) == 18 and body["table"]["columns"][-1] == "Source"
    assert body["sources"] == [{"document": "BOQ_Phase1.xlsx", "location": "Sheet BOQ", "snippet": ""}]
    assert body["steps"][0].endswith(": 18 rows")


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (AIUnavailableError("Add your GROQ_API_KEY"), 503, "AI_UNAVAILABLE"),
        (AIRateLimitedError("wait"), 429, "AI_RATE_LIMITED"),
    ],
)
def test_ai_errors_have_their_own_codes(loaded, error, status, code):
    loaded.app.state.lens.llm = FakeLLM([error])
    response = loaded.post("/api/chat", json={"question": "hi"})
    assert response.status_code == status and error_code(response) == code


def test_unexpected_error_is_internal_error_not_a_crash(loaded):
    loaded.app.state.lens.llm = FakeLLM([RuntimeError("boom")])
    browser = TestClient(loaded.app, raise_server_exceptions=False)  # see the response a real client gets
    response = browser.post("/api/chat", json={"question": "hi"})
    assert response.status_code == 500 and error_code(response) == "INTERNAL_ERROR"
    assert "boom" not in response.text  # internals stay in the server log


def test_upload_saves_files_safely_and_loads_them(client, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "UPLOADS_DIR", tmp_path / ".uploads")
    files = [
        ("files", ("../../BOQ_Phase1.xlsx", (SAMPLE_DIR / "BOQ_Phase1.xlsx").read_bytes())),
        ("files", ("Contract_A.pdf", (SAMPLE_DIR / "Contract_A.pdf").read_bytes())),
        ("files", ("contract_a.pdf", (SAMPLE_DIR / "Corrupt_Report.pdf").read_bytes())),
    ]
    body = client.post("/api/documents/upload", files=files).json()
    assert sorted(d["name"] for d in body["documents"]) == ["BOQ_Phase1.xlsx", "Contract_A.pdf", "contract_a (2).pdf"]
    assert {d["status"] for d in body["documents"]} == {"ok", "corrupt"}
    assert Path(body["folder"]).parent == tmp_path / ".uploads"  # "../../" did not escape the upload folder


def test_old_upload_folders_are_removed(client, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_store, "UPLOADS_DIR", tmp_path / ".uploads")
    pdf = ("files", ("Contract_A.pdf", (SAMPLE_DIR / "Contract_A.pdf").read_bytes()))
    for _ in range(upload_store.KEEP_UPLOADS + 2):
        client.post("/api/documents/upload", files=[pdf])
    assert len(list((tmp_path / ".uploads").iterdir())) == upload_store.KEEP_UPLOADS


def test_loading_steps_name_each_file(client):
    state = client.app.state.lens
    seen = []
    original = state.show_reading
    state.show_reading = lambda name: (original(name), seen.append(state.loading_step))
    client.post("/api/documents/load", json={"folder_path": str(SAMPLE_DIR)})
    assert "Reading BOQ_Phase1.xlsx" in seen
    assert client.get("/api/health").json()["loading_step"] is None
