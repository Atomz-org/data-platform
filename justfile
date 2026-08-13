# All recipes delegate to the `pf` CLI so nothing requires `just`.
default:            ; @uv run pf --help
new-group group:    ; @uv run pf new-group {{group}}
new-project g p:    ; @uv run pf new-project {{g}} {{p}}
work g p:           ; @uv run pf work {{g}} {{p}}
kg g p:             ; @uv run pf kg build {{g}} {{p}}
card g p:           ; @uv run pf kg card {{g}} {{p}}
impact g p node:    ; @uv run pf impact {{g}} {{p}} {{node}}
seed g p:           ; @uv run pf seed {{g}} {{p}}
run-all g:          ; @uv run pf run-all {{g}}
check:              ; @uv run pf check
tokens:             ; @uv run pf tokens
ui:                 ; @uv run pf ui

# tools
tools g p:          ; @uv run pf tool list {{g}} {{p}}
tool-doctor g p:    ; @uv run pf tool doctor {{g}} {{p}}
review g p:         ; @uv run pf tool recce run {{g}} {{p}}
review-ui g p:      ; @uv run pf tool recce serve {{g}} {{p}}
baseline g p:       ; @uv run pf tool recce baseline {{g}} {{p}}
