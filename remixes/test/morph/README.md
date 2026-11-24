# morph (test remix)

MORPH alone with STORE (which it saves through) and the stock effects, for its gates:
`tools/morph/test_morph.py` runs `morph.s` from its source text (the window, the clock, saving
against mocks of STORE's file calls); `tools/morph/port_morph.py` builds this remix, boots it under
the port with a project (`OT_PROJECT`), opens the window with [T1]+[UP], sets STEPS and x, closes
it with YES and reads the per-track weights; then the long press on T2, on the main page and on the
MIXER page.
