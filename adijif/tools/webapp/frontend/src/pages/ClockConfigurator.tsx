import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  Button,
  IconButton,
  Alert,
  Slider,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { clockApi } from '../api/client'

interface OutputClock {
  value: number
  name: string
}

export default function ClockConfigurator() {
  const [selectedPart, setSelectedPart] = useState('')
  const [referenceClock, setReferenceClock] = useState(125000000)
  const [outputClocks, setOutputClocks] = useState<OutputClock[]>([
    { value: 125000000, name: 'CLK1' },
    { value: 125000000, name: 'CLK2' },
  ])
  const [properties, setProperties] = useState<any>(null)
  const [selections, setSelections] = useState<Record<string, any>>({})
  const [solution, setSolution] = useState<any>(null)
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null)

  // Fetch supported clocks
  const { data: supportedClocks } = useQuery({
    queryKey: ['supportedClocks'],
    queryFn: async () => {
      const response = await clockApi.getSupportedClocks()
      return response.data
    },
  })

  // Fetch configurable properties when part is selected
  useEffect(() => {
    if (selectedPart) {
      clockApi.getConfigurableProperties(selectedPart).then((res) => {
        setProperties(res.data)
        setSelections({})
      })
    }
  }, [selectedPart])

  // Solve clock configuration
  const solveMutation = useMutation({
    mutationFn: async () => {
      const config = {
        part: selectedPart,
        reference_clock: referenceClock,
        output_clocks: outputClocks.map((c) => c.value),
        output_names: outputClocks.map((c) => c.name),
        selections: selections,
      }
      const response = await clockApi.solveConfig(selectedPart, config)
      return response.data
    },
    onSuccess: (data) => {
      setSolution(data)
      if (data.success) {
        fetchDiagram()
      }
    },
  })

  const fetchDiagram = async () => {
    const config = {
      part: selectedPart,
      reference_clock: referenceClock,
      output_clocks: outputClocks.map((c) => c.value),
      output_names: outputClocks.map((c) => c.name),
      selections: selections,
    }

    try {
      const response = await clockApi.getDiagram(selectedPart, config)
      const url = URL.createObjectURL(response.data)
      setDiagramUrl(url)
    } catch (error) {
      console.error('Failed to fetch diagram:', error)
    }
  }

  const handleAddOutput = () => {
    setOutputClocks([
      ...outputClocks,
      { value: 125000000, name: `CLK${outputClocks.length + 1}` },
    ])
  }

  const handleRemoveOutput = (index: number) => {
    setOutputClocks(outputClocks.filter((_, i) => i !== index))
  }

  const handleOutputChange = (index: number, field: 'value' | 'name', value: any) => {
    const updated = [...outputClocks]
    updated[index][field] = value
    setOutputClocks(updated)
  }

  const handleSelectionChange = (prop: string, value: any) => {
    setSelections((prev) => ({
      ...prev,
      [prop]: value,
    }))
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Clock Configurator
      </Typography>

      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Select a Part</InputLabel>
        <Select
          value={selectedPart}
          label="Select a Part"
          onChange={(e) => setSelectedPart(e.target.value)}
        >
          {supportedClocks?.map((part) => (
            <MenuItem key={part} value={part}>
              {part.toUpperCase().replace('_', '-')}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedPart && (
        <>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Clock Inputs and Outputs</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Reference Clock (Hz)"
                    value={referenceClock}
                    onChange={(e) => setReferenceClock(Number(e.target.value))}
                    inputProps={{
                      min: 1,
                      max: 1e9,
                      step: 1,
                    }}
                  />
                </Grid>

                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                      <Typography variant="subtitle1">Output Clocks</Typography>
                      <Button
                        startIcon={<AddIcon />}
                        onClick={handleAddOutput}
                        disabled={outputClocks.length >= 10}
                      >
                        Add Output
                      </Button>
                    </Box>

                    {outputClocks.map((output, index) => (
                      <Grid container spacing={2} key={index} sx={{ mb: 2 }}>
                        <Grid item xs={5}>
                          <TextField
                            fullWidth
                            type="number"
                            label={`Output Clock ${index + 1} (Hz)`}
                            value={output.value}
                            onChange={(e) =>
                              handleOutputChange(index, 'value', Number(e.target.value))
                            }
                            inputProps={{
                              min: 1,
                              max: 1e9,
                              step: 1,
                            }}
                          />
                        </Grid>
                        <Grid item xs={5}>
                          <TextField
                            fullWidth
                            label={`Output Clock Name ${index + 1}`}
                            value={output.name}
                            onChange={(e) => handleOutputChange(index, 'name', e.target.value)}
                          />
                        </Grid>
                        <Grid item xs={2}>
                          <IconButton
                            onClick={() => handleRemoveOutput(index)}
                            disabled={outputClocks.length <= 1}
                            color="error"
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Grid>
                      </Grid>
                    ))}
                  </Paper>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          {properties && (
            <Accordion defaultExpanded sx={{ mt: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Internal Clock Configuration</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  {Object.entries(properties).map(([prop, data]: [string, any]) => (
                    <Grid item xs={12} key={prop}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          {prop}
                        </Typography>
                        {data.description && (
                          <Typography variant="caption" color="text.secondary" gutterBottom>
                            {data.description}
                          </Typography>
                        )}

                        {data.options.length > 16 ? (
                          <Box sx={{ mt: 2, px: 1 }}>
                            <Slider
                              value={
                                selections[prop]
                                  ? [selections[prop].start, selections[prop].end]
                                  : [Math.min(...data.options), Math.max(...data.options)]
                              }
                              onChange={(_, value) =>
                                handleSelectionChange(prop, {
                                  start: (value as number[])[0],
                                  end: (value as number[])[1],
                                })
                              }
                              valueLabelDisplay="auto"
                              min={Math.min(...data.options)}
                              max={Math.max(...data.options)}
                            />
                          </Box>
                        ) : (
                          <FormControl fullWidth sx={{ mt: 1 }}>
                            <InputLabel>{prop}</InputLabel>
                            <Select
                              multiple
                              value={selections[prop] || []}
                              label={prop}
                              onChange={(e) => handleSelectionChange(prop, e.target.value)}
                            >
                              {data.options.map((option: any) => (
                                <MenuItem key={option} value={option}>
                                  {option}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        )}
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </AccordionDetails>
            </Accordion>
          )}

          <Box sx={{ mt: 3, mb: 3 }}>
            <Button
              variant="contained"
              size="large"
              onClick={() => solveMutation.mutate()}
              disabled={solveMutation.isPending}
            >
              {solveMutation.isPending ? 'Solving...' : 'Solve Configuration'}
            </Button>
          </Box>

          {solution && (
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Found Configuration</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {solution.success ? (
                  <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                    <pre style={{ overflow: 'auto' }}>
                      {JSON.stringify(solution.config, null, 2)}
                    </pre>
                  </Paper>
                ) : (
                  <Alert severity="warning">
                    No valid configuration found: {solution.error}
                  </Alert>
                )}
              </AccordionDetails>
            </Accordion>
          )}

          {diagramUrl && solution?.success && (
            <Accordion defaultExpanded sx={{ mt: 2 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Diagram</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box
                  component="img"
                  src={diagramUrl}
                  alt="Clock Diagram"
                  sx={{ width: '100%', height: 'auto' }}
                />
              </AccordionDetails>
            </Accordion>
          )}
        </>
      )}
    </Box>
  )
}
