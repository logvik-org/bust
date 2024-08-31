from bust.utils import NL, indent_string


def if_stmt(condition: str, if_true: str):
    # fmt: off
    return (
        f"if {condition} then{NL}"
        f"{indent_string(if_true)}{NL}"
        f"end if;{NL}"
    )  # fmt: on


def if_else_stmt(condition: str, if_true: str, else_true: str):
    return (
        f"if {condition} then{NL}"
        f"{indent_string(if_true)}{NL}"
        f"else{NL}"
        f"{indent_string(else_true)}{NL}"
        "end if;"
    )


def if_elseif_stmt(
    condition: str, if_true: str, elseif_condition: str, elseif_true: str
):
    return (
        f"if {condition} then{NL}"
        f"{indent_string(if_true)}{NL}"
        f"elsif {elseif_condition} then{NL}"
        f"{indent_string(elseif_true)}{NL}"
        f"end if;{NL}"
    )


def if_elseif_else_stmt(
    condition: str,
    if_true: str,
    elseif_condition: str,
    elseif_true: str,
    else_true: str,
):
    return (
        f"if {condition} then{NL}"
        f"{indent_string(if_true)}{NL}"
        f"elsif {elseif_condition} then{NL}"
        f"{indent_string(elseif_true)}{NL}"
        f"else{NL}"
        f"{indent_string(else_true)}{NL}"
        f"end if;{NL}"
    )
