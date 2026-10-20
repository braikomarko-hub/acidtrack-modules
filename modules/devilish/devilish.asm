; dEVILish -- the DSP half: a pass-through. The Devil Fish mods live inside the
; TB-303's circuit, so OCTA303's voice applies them on the ColdFire, reading this
; slot's knobs from the live lane. Shape of modules/tapeecho/cpu_passthrough.asm
; (proven on hardware, EUCLACID's too): a counted, empty sample loop.
init:
        rts
proc:
        do      n7,>dv_pass_end
        nop
dv_pass_end:
        rts
