package main

import (
	"C"

	"context"
	// "io/ioutil"
	"log/slog"

	"oss.terrastruct.com/d2/d2graph"
	// "oss.terrastruct.com/d2/d2layouts/d2dagrelayout"
	"oss.terrastruct.com/d2/d2layouts/d2elklayout"
	"oss.terrastruct.com/d2/d2lib"
	"oss.terrastruct.com/d2/d2renderers/d2svg"
	"oss.terrastruct.com/d2/d2themes/d2themescatalog"
	"oss.terrastruct.com/d2/lib/textmeasure"
	"oss.terrastruct.com/util-go/go2"
)

//export runme
func runme(namePtr *C.char) *C.char {

	slog.Info("runme")
	graph := C.GoString(namePtr)
	//   log.Println(graph)

	ruler, _ := textmeasure.NewRuler()
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
	ctx := context.Background()
	diagram, _, _ := d2lib.Compile(ctx, graph, compileOpts, renderOpts)
	out, _ := d2svg.Render(diagram, renderOpts)
	// _ = ioutil.WriteFile(filepath.Join("out.svg"), out, 0600)

	// Convert []byte to string
	outs := string(out)

	return C.CString(outs)
}

func main() {

}
