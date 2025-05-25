import os
import json
import datetime
import streamlit as st
import re
from pathlib import Path
import shutil
from utils.logging_config import setup_logger

# 로거 설정
logger = setup_logger(__name__)

# RAG 저장소 경로 설정
RAG_STORE_DIR = Path("/Users/idongju/dev/dev-tool-with-llm/chatbot/dj/front/rag_store")

# 지원되는 파일 형식
SUPPORTED_FILE_FORMATS = {
    "텍스트 파일 (*.txt)": "txt",
    "마크다운 파일 (*.md)": "md",
    "PDF 파일 (*.pdf)": "pdf",  # PDF 지원 추가
}

def initialize_rag_store():
    """RAG 저장소 디렉토리 초기화"""
    if not RAG_STORE_DIR.exists():
        RAG_STORE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"RAG 저장소 디렉토리 생성: {RAG_STORE_DIR}")
    
    # 메타데이터 파일이 없으면 생성
    metadata_file = RAG_STORE_DIR / "metadata.json"
    if not metadata_file.exists():
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        logger.info(f"메타데이터 파일 생성: {metadata_file}")

def load_metadata():
    """메타데이터 파일 로드"""
    metadata_file = RAG_STORE_DIR / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("메타데이터 파일 읽기 오류, 새로운 메타데이터 생성")
            return []
    return []

def save_metadata(metadata):
    """메타데이터 파일 저장"""
    metadata_file = RAG_STORE_DIR / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info("메타데이터 저장 완료")

def convert_to_markdown(text):
    """텍스트를 마크다운 형식으로 변환"""
    lines = text.split('\n')
    md_lines = []
    
    # 이전 라인이 제목인지 확인하기 위한 변수
    previous_is_title = False
    in_list = False
    
    for i, line in enumerate(lines):
        line = line.rstrip()
        
        # 빈 줄 처리
        if not line.strip():
            md_lines.append("")
            previous_is_title = False
            in_list = False
            continue
        
        # 숫자로 시작하는 섹션 제목 (예: "1. 통합 자연어 인터페이스")
        if re.match(r'^\d+\.\s+[A-Z가-힣]', line):
            # 이전에 빈 줄이 없으면 추가
            if i > 0 and md_lines[-1]:
                md_lines.append("")
            md_lines.append(f"## {line}")
            previous_is_title = True
            in_list = False
            continue
        
        # 대문자나 한글로 시작하는 짧은 단어가 줄의 시작이면 제목으로 처리
        if (line[0].isupper() or '\uAC00' <= line[0] <= '\uD7A3') and len(line.split()) < 5 and i > 0 and not lines[i-1].strip() and not previous_is_title:
            md_lines.append(f"### {line}")
            previous_is_title = True
            in_list = False
            continue
        
        # 문장 안에 콜론(:)이 있고 그 뒤에 내용이 있으면 강조 표시
        if ': ' in line and not line.startswith('-') and not line.startswith('*'):
            parts = line.split(': ', 1)
            md_lines.append(f"**{parts[0]}**: {parts[1]}")
            previous_is_title = False
            continue
        
        # 불릿 리스트 변환 (줄이 "-"로 시작하거나 숫자와 점으로 시작하는 경우)
        if line.strip().startswith('-') or re.match(r'^\s*\d+\.\s', line):
            # 이미 불릿 형태면 그대로 추가
            md_lines.append(line)
            previous_is_title = False
            in_list = True
            continue
        
        # 예시나 코드 블록으로 보이는 텍스트
        if line.startswith('"') and line.endswith('"') and len(line) < 100:
            if not in_list:
                md_lines.append("```")
                md_lines.append(line.strip('"'))
                md_lines.append("```")
            else:
                md_lines.append(f"  {line}")
            previous_is_title = False
            continue
        
        # 기타 일반 텍스트
        md_lines.append(line)
        previous_is_title = False
    
    return '\n'.join(md_lines)

def save_uploaded_file(uploaded_file, collection_name, description="", convert_md=False):
    """업로드된 파일을 저장하고 메타데이터 업데이트"""
    # 파일 확장자 추출
    file_ext = Path(uploaded_file.name).suffix.lstrip('.').lower()
    
    # 현재 시간으로 파일명 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{collection_name}_{timestamp}.{file_ext}"
    file_path = RAG_STORE_DIR / filename
    
    # 파일 저장
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 마크다운 변환이 요청된 경우
    md_file_path = None
    if convert_md and file_ext == 'txt':
        try:
            # 텍스트 파일 내용 읽기
            content = uploaded_file.getvalue().decode('utf-8', errors='replace')
            
            # 마크다운으로 변환
            md_content = convert_to_markdown(content)
            
            # 마크다운 파일로 저장
            md_filename = f"{collection_name}_{timestamp}.md"
            md_file_path = RAG_STORE_DIR / md_filename
            
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            logger.info(f"마크다운 변환 파일 저장: {md_file_path}")
        except Exception as e:
            logger.error(f"마크다운 변환 중 오류 발생: {str(e)}")
    
    # 메타데이터 업데이트
    metadata = load_metadata()
    new_entry = {
        "id": len(metadata) + 1,
        "filename": filename,
        "original_filename": uploaded_file.name,
        "collection_name": collection_name,
        "description": description,  # 설명 필드 추가
        "file_format": file_ext,
        "created_at": datetime.datetime.now().isoformat(),
        "file_path": str(file_path),
        "file_size": os.path.getsize(file_path),
        "markdown_file_path": str(md_file_path) if md_file_path else None
    }
    
    metadata.append(new_entry)
    save_metadata(metadata)
    
    return new_entry

def delete_document(document_id):
    """문서 및 메타데이터에서 항목 삭제"""
    metadata = load_metadata()
    
    # 삭제할 문서 찾기
    doc_to_delete = None
    updated_metadata = []
    
    for doc in metadata:
        if doc["id"] == document_id:
            doc_to_delete = doc
        else:
            updated_metadata.append(doc)
    
    if doc_to_delete:
        # 파일 삭제
        file_path = Path(doc_to_delete["file_path"])
        if file_path.exists():
            file_path.unlink()
            logger.info(f"문서 삭제 완료: {file_path}")
        
        # 마크다운 파일이 있으면 함께 삭제
        if doc_to_delete.get("markdown_file_path"):
            md_path = Path(doc_to_delete["markdown_file_path"])
            if md_path.exists():
                md_path.unlink()
                logger.info(f"마크다운 파일 삭제 완료: {md_path}")
        
        # 메타데이터 업데이트
        save_metadata(updated_metadata)
        return True
    
    return False

def create_rag(document_id):
    """RAG 생성 (향후 구현)"""
    # 향후 RAG 생성 기능 구현
    logger.info(f"문서 ID {document_id}에 대한 RAG 생성 요청")
    return True

def read_text_file(file_path):
    """텍스트 파일 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # UTF-8로 읽기 실패 시 다른 인코딩 시도
        try:
            with open(file_path, 'r', encoding='cp949') as f:
                return f.read()
        except UnicodeDecodeError:
            return "파일 인코딩을 확인할 수 없습니다. 파일이 텍스트 형식인지 확인해주세요."
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"

def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.header("RAG 도구 설정")
        
        # 기존 문서 목록 표시
        st.subheader("저장된 문서")
        metadata = load_metadata()
        
        if not metadata:
            st.info("저장된 문서가 없습니다.")
        else:
            for doc in metadata:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{doc['collection_name']}**")
                    if doc.get('description'):  # 설명이 있으면 표시
                        st.caption(f"설명: {doc['description']}")
                    st.caption(f"파일: {doc.get('original_filename', doc['filename'])}")
                    st.caption(f"형식: {doc['file_format']}, 생성: {doc['created_at'][:10]}")
                    if doc.get("markdown_file_path"):
                        st.caption("마크다운 변환: ✓")
                with col2:
                    if st.button("로드", key=f"load_{doc['id']}"):
                        st.session_state.selected_document = doc
                        st.rerun()

def rag_page():
    """RAG 페이지 메인 함수"""
    st.title("RAG 문서 관리")
    
    # RAG 저장소 초기화
    initialize_rag_store()
    
    # 세션 상태 초기화
    if "collection_name" not in st.session_state:
        st.session_state.collection_name = ""
    if "description" not in st.session_state:  # 설명 필드 세션 상태 추가
        st.session_state.description = ""
    if "selected_format" not in st.session_state:
        st.session_state.selected_format = next(iter(SUPPORTED_FILE_FORMATS.keys()))
    if "selected_document" not in st.session_state:
        st.session_state.selected_document = None
    if "convert_to_md" not in st.session_state:
        st.session_state.convert_to_md = False
    
    # 사이드바 렌더링
    render_sidebar()
    
    # 메인 컨텐츠 영역
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("문서 불러오기")
        
        # 컬렉션 이름 입력
        collection_name = st.text_input(
            "컬렉션 이름",
            value=st.session_state.collection_name,
            help="문서를 구분할 수 있는 고유한 이름을 입력하세요."
        )
        
        # 문서 설명 입력 필드 추가
        description = st.text_area(
            "문서 설명",
            value=st.session_state.description,
            height=100,
            help="이 문서의 목적과 RAG 임베딩을 하는 이유를 설명해주세요."
        )
        
        # 파일 형식 선택
        selected_format = st.selectbox(
            "파일 형식",
            options=list(SUPPORTED_FILE_FORMATS.keys()),
            index=list(SUPPORTED_FILE_FORMATS.keys()).index(st.session_state.selected_format)
        )
        
        # 파일 확장자 설정
        file_format = SUPPORTED_FILE_FORMATS[selected_format]
        
        # 텍스트 파일이면 마크다운 변환 옵션 표시
        convert_to_md = False
        if file_format == 'txt':
            convert_to_md = st.checkbox(
                "텍스트를 마크다운으로 변환",
                value=st.session_state.convert_to_md,
                help="텍스트 파일을 마크다운 형식으로 자동 변환합니다."
            )
            st.session_state.convert_to_md = convert_to_md
        
        # 파일 업로더
        uploaded_file = st.file_uploader(
            "문서 파일 업로드",
            type=[file_format],
            help=f"지원되는 형식: .{file_format}"
        )
        
        # 버튼 영역
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            save_btn = st.button("저장", use_container_width=True)
            if save_btn:
                if not collection_name:
                    st.error("컬렉션 이름을 입력해주세요.")
                elif not uploaded_file:
                    st.error("파일을 업로드해주세요.")
                else:
                    with st.spinner("파일 처리 중..."):
                        doc = save_uploaded_file(
                            uploaded_file, 
                            collection_name,
                            description=description,  # 설명 전달
                            convert_md=convert_to_md
                        )
                        success_msg = f"문서가 성공적으로 저장되었습니다: {doc['filename']}"
                        if doc.get("markdown_file_path"):
                            success_msg += " (마크다운 변환 완료)"
                        st.success(success_msg)
                        st.session_state.collection_name = ""
                        st.session_state.description = ""  # 설명 필드 초기화
                        st.session_state.selected_document = doc
                        st.rerun()
        
        with col_btn2:
            if st.button("삭제", use_container_width=True):
                if st.session_state.selected_document:
                    if delete_document(st.session_state.selected_document["id"]):
                        st.success("문서가 성공적으로 삭제되었습니다.")
                        st.session_state.selected_document = None
                        st.rerun()
                else:
                    st.error("삭제할 문서를 선택해주세요.")
        
        with col_btn3:
            if st.button("RAG 생성", use_container_width=True):
                if st.session_state.selected_document:
                    with st.spinner("RAG 생성 중..."):
                        if create_rag(st.session_state.selected_document["id"]):
                            st.success("RAG가 성공적으로 생성되었습니다.")
                else:
                    st.error("RAG를 생성할 문서를 선택해주세요.")
    
    with col2:
        st.subheader("문서 미리보기")
        
        if st.session_state.selected_document:
            doc = st.session_state.selected_document
            st.write(f"**컬렉션**: {doc['collection_name']}")
            # 설명 표시 추가
            if doc.get('description'):
                st.write(f"**설명**: {doc['description']}")
            st.write(f"**파일**: {doc.get('original_filename', doc['filename'])}")
            st.write(f"**생성일**: {doc['created_at'][:10]}")
            st.write(f"**형식**: {doc['file_format']}")
            
            # 마크다운 변환 여부 표시
            if doc.get("markdown_file_path"):
                st.write("**마크다운 변환**: ✓")
            
            st.divider()
            
            # 탭 설정 - 원본 및 마크다운 변환본
            if doc.get("markdown_file_path"):
                tab1, tab2 = st.tabs(["원본", "마크다운 변환"])
                
                with tab1:
                    # 원본 파일 내용 표시
                    file_path = doc['file_path']
                    file_format = doc['file_format'].lower()
                    
                    if file_format in ['txt', 'md']:
                        # 텍스트 파일 내용 표시
                        content = read_text_file(file_path)
                        st.text_area("원본 내용", value=content, height=400, disabled=True)
                    elif file_format == 'pdf':
                        # PDF 파일 표시 (향후 구현)
                        st.info("PDF 파일 미리보기는 아직 구현되지 않았습니다.")
                        st.write(f"파일 경로: {file_path}")
                    else:
                        st.info(f"'{file_format}' 형식 미리보기는 지원되지 않습니다.")
                
                with tab2:
                    # 마크다운 변환 내용 표시
                    md_content = read_text_file(doc["markdown_file_path"])
                    st.markdown(md_content)
                    st.download_button(
                        "마크다운 파일 다운로드",
                        md_content,
                        file_name=f"{doc['collection_name']}_converted.md",
                        mime="text/markdown"
                    )
            else:
                # 원본 파일 내용만 표시
                file_path = doc['file_path']
                file_format = doc['file_format'].lower()
                
                if file_format in ['txt', 'md']:
                    # 텍스트/마크다운 파일 내용 표시
                    content = read_text_file(file_path)
                    
                    if file_format == 'md':
                        st.markdown(content)
                    else:
                        st.text_area("내용", value=content, height=400, disabled=True)
                        
                        # 텍스트 파일의 경우 마크다운 변환 버튼 추가
                        if st.button("마크다운으로 변환"):
                            md_content = convert_to_markdown(content)
                            st.markdown("### 마크다운 미리보기")
                            st.markdown(md_content)
                            
                            # 마크다운 다운로드 버튼
                            st.download_button(
                                "마크다운 파일 다운로드",
                                md_content,
                                file_name=f"{doc['collection_name']}_converted.md",
                                mime="text/markdown"
                            )
                elif file_format == 'pdf':
                    # PDF 파일 표시 (향후 구현)
                    st.info("PDF 파일 미리보기는 아직 구현되지 않았습니다.")
                    st.write(f"파일 경로: {file_path}")
                else:
                    st.info(f"'{file_format}' 형식 미리보기는 지원되지 않습니다.")
        else:
            st.info("미리보기할 문서를 선택해주세요.")
            
            # 업로드 중인 파일 미리보기
            if 'uploaded_file' in locals() and uploaded_file is not None:
                st.divider()
                st.caption("업로드 중인 파일:")
                
                if file_format in ['txt', 'md']:
                    # 텍스트 파일 내용 표시
                    try:
                        content = uploaded_file.getvalue().decode('utf-8', errors='replace')
                    except:
                        try:
                            content = uploaded_file.getvalue().decode('cp949', errors='replace')
                        except:
                            content = "파일 내용을 디코딩할 수 없습니다."
                    
                    # 탭으로 원본과 변환 미리보기 제공
                    if file_format == 'txt' and convert_to_md:
                        tab1, tab2 = st.tabs(["원본", "마크다운 변환 미리보기"])
                        
                        with tab1:
                            st.text_area(
                                "업로드 중인 파일 내용", 
                                value=content,
                                height=300,
                                disabled=True
                            )
                        
                        with tab2:
                            md_content = convert_to_markdown(content)
                            st.markdown(md_content)
                    else:
                        if file_format == 'md':
                            st.markdown(content)
                        else:
                            st.text_area(
                                "업로드 중인 파일 미리보기", 
                                value=content,
                                height=300,
                                disabled=True
                            )
                elif file_format == 'pdf':
                    st.write(f"파일명: {uploaded_file.name}")
                    st.info("PDF 파일 미리보기는 아직 구현되지 않았습니다.")
                else:
                    st.write(f"파일명: {uploaded_file.name}")
                    st.info(f"'{file_format}' 형식 미리보기는 지원되지 않습니다.") 