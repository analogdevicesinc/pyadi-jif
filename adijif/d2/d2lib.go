package main

import (
	"C"

	"context"

	cdrslog "cdr.dev/slog"

	"oss.terrastruct.com/d2/d2graph"
	"oss.terrastruct.com/d2/d2layouts/d2elklayout"
	"oss.terrastruct.com/d2/d2lib"
	"oss.terrastruct.com/d2/d2renderers/d2svg"
	"oss.terrastruct.com/d2/d2themes/d2themescatalog"
	"oss.terrastruct.com/d2/lib/log"
	"oss.terrastruct.com/d2/lib/textmeasure"
	"oss.terrastruct.com/util-go/go2"
)

//export runme
func runme(namePtr *C.char) *C.char {
	graph := C.GoString(namePtr)

	ruler, err := textmeasure.NewRuler()
	if err != nil {
		return C.CString("error: failed to create ruler")
	}
	layoutResolver := func(engine string) (d2graph.LayoutGraph, error) {
		return d2elklayout.DefaultLayout, nil
	}
	renderOpts := &d2svg.RenderOpts{
		Pad:         go2.Pointer(int64(5)),
		ThemeID:     &d2themescatalog.CoolClassics.ID,
		DarkThemeID: &d2themescatalog.DarkMauve.ID,
	}
	compileOpts := &d2lib.CompileOptions{
		LayoutResolver: layoutResolver,
		Ruler:          ruler,
	}

	logger := cdrslog.Make()
	ctx := log.With(context.Background(), logger) // Changed WithLogger to With

	diagram, _, err := d2lib.Compile(ctx, graph, compileOpts, renderOpts)
	if err != nil {
		return C.CString("error: failed to compile diagram")
	}
	out, err := d2svg.Render(diagram, renderOpts)
	if err != nil {
		return C.CString("error: failed to render SVG")
	}

	outs := string(out)
	return C.CString(outs)
}

func main() {

}
