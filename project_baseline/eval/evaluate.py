"""
evaluate.py
=======================

시나리오 호출 평가를 수행하는 스크립트입니다.

평가 항목 (Rule-based, Ground Truth 불필요):
1. Correct Function Name - 올바른 함수 호출 여부
2. Valid Arguments - 인자 타입/포맷 정확성
3. No Hallucinated Calls - 정의되지 않은 함수 방지
사용법:
    python evaluate.py \
        --input sample_data/toolcall_single_turn_multi_tool_sample_kr.json \
        --output results.json
    
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# .env 파일 로드 (있는 경우)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv가 없어도 상관없음

# 참고: BFCL(ast_checker)은 possible_answer(ground truth)가 필요하므로
# 현재 프로젝트에서는 사용하지 않습니다. Rule-based 평가만 수행합니다.


def extract_all_turns_from_assistant(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    대화 메시지에서 모든 assistant의 tool_calls를 턴별로 추출 (Multi Turn용)
    
    Args:
        messages: 대화 메시지 리스트
    
    Returns:
        턴별 tool_calls 리스트 [[턴1_tool_calls], [턴2_tool_calls], ...]
    """
    turns = []
    for msg in messages:
        if msg.get("role") == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:  # tool_calls가 있는 턴만 추가
                turns.append(tool_calls)
    return turns


def extract_tools_from_metadata(metadata_str: str) -> List[Dict[str, Any]]:
    """
    metadata에서 tools 정의 추출
    
    Args:
        metadata_str: JSON 문자열 형식의 metadata
    
    Returns:
        tools 리스트
    """
    try:
        metadata = json.loads(metadata_str)
        return metadata.get("tools", [])
    except (json.JSONDecodeError, TypeError):
        return []


def find_function_definition(
    func_name: str,
    tools: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    함수 이름으로 함수 정의 찾기
    
    Args:
        func_name: 찾을 함수 이름
        tools: 사용 가능한 도구 정의 리스트
    
    Returns:
        함수 정의 딕셔너리 또는 None
    """
    for tool in tools:
        if tool.get("type") == "function":
            function_def = tool.get("function")
            if function_def and function_def.get("name") == func_name:
                return function_def
    return None


def validate_function_definition_structure(
    func_name: str,
    func_def: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    함수 정의 구조 검증
    
    Args:
        func_name: 함수 이름
        func_def: 함수 정의 딕셔너리
    
    Returns:
        (검증 통과 여부, 오류 메시지 리스트)
    """
    errors = []
    
    if "name" not in func_def:
        errors.append(f"[{func_name}] 함수 정의에 'name' 필드가 없음")
    
    if func_def.get("name") != func_name:
        errors.append(f"[{func_name}] 함수 정의의 name이 일치하지 않음: {func_def.get('name')}")
    
    if "parameters" not in func_def:
        errors.append(f"[{func_name}] 함수 정의에 'parameters' 필드가 없음")
        return len(errors) == 0, errors
    
    parameters = func_def.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append(f"[{func_name}] 함수 정의의 'parameters'가 딕셔너리가 아님")
        return len(errors) == 0, errors
    
    if parameters.get("type") != "object":
        errors.append(f"[{func_name}] 함수 정의의 parameters.type이 'object'가 아님: {parameters.get('type')}")
    
    if "properties" not in parameters:
        errors.append(f"[{func_name}] 함수 정의의 parameters에 'properties' 필드가 없음")
    
    return len(errors) == 0, errors


def check_hallucinated_calls(
    tool_calls: List[Dict[str, Any]],
    available_tools: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    정의되지 않은 함수 호출 여부 확인
    
    Args:
        tool_calls: 모델이 생성한 tool_calls
        available_tools: 사용 가능한 도구 정의 리스트
    
    Returns:
        (모든 함수가 정의됨, 오류 메시지 리스트)
    """
    available_func_names = set()
    for tool in available_tools:
        if tool.get("type") == "function":
            func_def = tool.get("function")
            if func_def and "name" in func_def:
                available_func_names.add(func_def["name"])
    
    errors = []
    for tool_call in tool_calls:
        func_info = tool_call.get("function", {})
        func_name = func_info.get("name")
        if func_name and func_name not in available_func_names:
            errors.append(f"정의되지 않은 함수 호출: {func_name}")
    
    return len(errors) == 0, errors


def _validate_type(value: Any, expected_type: str) -> bool:
    """
    타입 검증 헬퍼 함수
    
    Args:
        value: 검증할 값
        expected_type: 기대하는 타입 (string, integer, number, boolean, array, object)
    
    Returns:
        타입 일치 여부
    """
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict
    }
    
    expected_python_type = type_mapping.get(expected_type)
    if expected_python_type is None:
        return True  # 알 수 없는 타입은 검증 통과
    
    if expected_type == "number":
        return isinstance(value, expected_python_type)
    return isinstance(value, expected_python_type)


def evaluate_single_tool_call(
    tool_call: Dict[str, Any],
    tools: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    단일 도구 호출 평가
    
    Args:
        tool_call: 평가할 도구 호출
        tools: 사용 가능한 도구 정의 리스트
    
    Returns:
        단일 도구 호출 평가 결과
    """
    func_info = tool_call.get("function", {})
    func_name = func_info.get("name", "unknown")
    
    # 인자 파싱
    pred_args = {}
    try:
        args_str = func_info.get("arguments", "{}")
        if isinstance(args_str, str):
            args = json.loads(args_str) if args_str.strip() else {}
        else:
            args = args_str if isinstance(args_str, dict) else {}
        pred_args = args
    except json.JSONDecodeError as e:
        return {
            "function_name": func_name,
            "valid": False,
            "errors": [f"인자 JSON 파싱 실패: {str(e)}"]
        }
    except Exception as e:
        return {
            "function_name": func_name,
            "valid": False,
            "errors": [f"인자 처리 오류: {str(e)}"]
        }
    
    tool_result = {
        "function_name": func_name,
        "valid": True,
        "errors": []
    }
    
    # 도구 정의 찾기
    func_def = find_function_definition(func_name, tools)
    
    if not func_def:
        tool_result["valid"] = False
        tool_result["errors"].append(f"정의되지 않은 함수: {func_name}")
        return tool_result
    
    # 함수 정의 구조 검증
    struct_valid, struct_errors = validate_function_definition_structure(func_name, func_def)
    if not struct_valid:
        tool_result["valid"] = False
        tool_result["errors"].extend(struct_errors)
        return tool_result
    
    # 필수 파라미터 확인
    parameters = func_def.get("parameters", {})
    required_params = parameters.get("required", [])
    param_properties = parameters.get("properties", {})
    
    missing_params = [p for p in required_params if p not in pred_args]
    if missing_params:
        tool_result["valid"] = False
        tool_result["errors"].append(f"필수 파라미터 누락: {missing_params}")
    
    # 타입 검증
    for param_name, param_value in pred_args.items():
        if param_name in param_properties:
            param_schema = param_properties[param_name]
            expected_type = param_schema.get("type")
            
            if expected_type:
                # 문자열로 전달된 숫자 처리 (예: "120" -> 120 for integer)
                if expected_type == "integer" and isinstance(param_value, str):
                    try:
                        param_value = int(param_value)
                        pred_args[param_name] = param_value  # 업데이트
                    except (ValueError, TypeError):
                        pass  # 변환 실패 시 원래 값으로 검증
                
                if not _validate_type(param_value, expected_type):
                    tool_result["valid"] = False
                    received_type = type(param_value).__name__
                    tool_result["errors"].append(
                        f"파라미터 '{param_name}' 타입 오류: {expected_type} 기대, {received_type} 받음"
                    )
        
    return tool_result


def evaluate_turn(
    tool_calls: List[Dict[str, Any]],
    tools: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    단일 턴(assistant 메시지)의 tool_calls 평가
    
    Args:
        tool_calls: 평가할 tool_calls 리스트
        tools: 사용 가능한 도구 정의 리스트
    
    Returns:
        턴 평가 결과 딕셔너리
    """
    turn_result = {
        "correct_function_name": False,
        "valid_arguments": False,
        "no_hallucinated_calls": False,
        "pass": False,
        "errors": [],
        "num_tool_calls": len(tool_calls),
        "tool_results": []
    }
    
    if len(tool_calls) == 0:
        return turn_result
    
    # 3. No Hallucinated Calls 확인
    halluc_ok, halluc_errors = check_hallucinated_calls(tool_calls, tools)
    turn_result["no_hallucinated_calls"] = halluc_ok
    turn_result["errors"].extend(halluc_errors)
    
    if not halluc_ok:
        return turn_result
    
    # 각 도구 호출 평가
    all_args_valid = True
    all_func_names_correct = True
    
    for tool_call in tool_calls:
        tool_result = evaluate_single_tool_call(
            tool_call=tool_call,
            tools=tools
        )
        
        turn_result["tool_results"].append(tool_result)
        
        # 1. Correct Function Name: evaluate_single_tool_call에서 이미 검증했으므로 결과 재사용
        func_info = tool_call.get("function", {})
        func_name = func_info.get("name", "unknown")
        has_definition_error = any(
            "정의되지 않은 함수" in err or "함수 정의" in err 
            for err in tool_result["errors"]
        )
        
        if has_definition_error:
            all_func_names_correct = False
        
        if not tool_result["valid"]:
            all_args_valid = False
            turn_result["errors"].extend([
                f"[{tool_result['function_name']}] {err}" 
                for err in tool_result["errors"]
            ])
    
    # 전체 결과 종합
    turn_result["correct_function_name"] = all_func_names_correct
    turn_result["valid_arguments"] = all_args_valid
    
    # 최종 통과 여부
    turn_result["pass"] = (
        turn_result["correct_function_name"] and
        turn_result["valid_arguments"] and
        turn_result["no_hallucinated_calls"]
    )
    
    return turn_result


def evaluate_entry(
    entry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Single Turn & Multi Turn 평가 수행 (각 턴별 평가)
    
    모든 assistant 메시지의 tool_calls를 턴별로 평가합니다.
    
    Args:
        entry: 평가할 데이터 항목
    
    Returns:
        평가 결과 딕셔너리 (턴별 결과 + 전체 결과)
    """
    row = entry.get("row", {})
    messages = row.get("messages", [])
    metadata_str = row.get("metadata", "{}")
    
    # 도구 정의 추출
    tools = extract_tools_from_metadata(metadata_str)
    
    # 모든 턴의 tool_calls 추출 (각 assistant 메시지별)
    turns = extract_all_turns_from_assistant(messages)
    
    result = {
        "correct_function_name": False,
        "valid_arguments": False,
        "no_hallucinated_calls": False,
        "pass": False,
        "errors": [],
        "num_turns": len(turns),
        "total_tool_calls": 0,
        "turn_results": []
    }
    
    # tool_calls가 있는 턴이 없으면 실패
    if len(turns) == 0:
        result["errors"].append("도구 호출이 있는 턴이 없습니다.")
        return result
    
    # Single Turn & Multi Use: 여러 도구 사용이 필요
    # 각 턴별 평가
    all_turns_pass = True
    for turn_idx, tool_calls in enumerate(turns, 1):
        turn_result = evaluate_turn(tool_calls, tools)
        turn_result["turn"] = turn_idx
        result["turn_results"].append(turn_result)
        result["total_tool_calls"] += len(tool_calls)
        
        if not turn_result["pass"]:
            all_turns_pass = False
            result["errors"].extend([
                f"[턴 {turn_idx}] {err}" 
                for err in turn_result["errors"]
            ])
    
    # 전체 결과 종합 (모든 턴이 통과해야 함)
    result["correct_function_name"] = all(
        turn["correct_function_name"] for turn in result["turn_results"]
    )
    result["valid_arguments"] = all(
        turn["valid_arguments"] for turn in result["turn_results"]
    )
    result["no_hallucinated_calls"] = all(
        turn["no_hallucinated_calls"] for turn in result["turn_results"]
    )
    result["pass"] = all_turns_pass
    
    return result


def load_data(input_path: str) -> List[Dict[str, Any]]:
    """
    입력 파일 로드 (JSON 또는 JSONL)
    
    Args:
        input_path: 입력 파일 경로
    
    Returns:
        데이터 항목 리스트
    """
    data = []
    
    if input_path.endswith(".jsonl"):
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                data = content
            elif isinstance(content, dict):
                # 단일 항목
                data = [content]
    
    return data


def evaluate_file(
    input_path: str,
    output_path: str
) -> None:
    """
    파일 전체 평가
    
    Args:
        input_path: 입력 파일 경로
        output_path: 출력 파일 경로
    """
    # 데이터 로드
    data = load_data(input_path)
        
    results = []
    for entry in data:
        entry_id = entry.get("row_idx") or entry.get("id", "unknown")
        
        try:
            result = evaluate_entry(
                entry=entry
            )
            results.append({
                "id": entry_id,
                **result
            })
        except Exception as e:
            results.append({
                "id": entry_id,
                "correct_function_name": False,
                "valid_arguments": False,
                "no_hallucinated_calls": False,
                "pass": False,
                "errors": [f"평가 중 오류 발생: {str(e)}"]
            })
    
    # 결과 저장
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 요약 출력
    total = len(results)
    passed = sum(1 for r in results if r.get("pass"))
    
    print(f"\n📊 평가 결과 요약")
    print(f"총 평가 항목: {total}")
    print(f"통과: {passed} ({passed/total*100:.1f}%)")
    print(f"실패: {total - passed} ({(total-passed)/total*100:.1f}%)")
    
    # 각 평가 항목별 통과율
    if total > 0:
        print(f"\n📋 평가 항목별 통과율:")
        print(f"  - Correct Function Name: {sum(1 for r in results if r.get('correct_function_name'))}/{total}")
        print(f"  - Valid Arguments: {sum(1 for r in results if r.get('valid_arguments'))}/{total}")
        print(f"  - No Hallucinated Calls: {sum(1 for r in results if r.get('no_hallucinated_calls'))}/{total}")
    
    print(f"\n✅ 상세 결과 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Single Turn & Multi Turn 도구 호출 평가"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="입력 파일 경로 (JSON 또는 JSONL)"
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="출력 파일 경로 (기본값: results.json)"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)
    
    evaluate_file(
        input_path=args.input,
        output_path=args.output
    )


if __name__ == "__main__":
    main()

