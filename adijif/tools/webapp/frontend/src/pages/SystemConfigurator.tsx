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
  Alert,
} from '@mui/material'
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { systemApi, converterApi, clockApi } from '../api/client'

export default function SystemConfigurator() {
  const [converterPart, setConverterPart] = useState('')
  const [clockPart, setClockPart] = useState('')
  const [fpgaDevKit, setFpgaDevKit] = useState('')
  const [referenceRate, setReferenceRate] = useState(125000000)
  const [sampleClock, setSampleClock] = useState(1e9)
  const [decimation, setDecimation] = useState(1)
  const [quickMode, setQuickMode] = useState('')
  const [jesdClass, setJesdClass] = useState('')
  const [refClockConstraint, setRefClockConstraint] = useState('Unconstrained')
  const [sysClkSelect, setSysClkSelect] = useState('XCVR_QPLL0')
  const [outClkSelect, setOutClkSelect] = useState<string[]>([])
  const [forcePll, setForcePll] = useState('Auto')
  const [solution, setSolution] = useState<any>(null)
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null)
  const [quickModes, setQuickModes] = useState<any>(null)

  // Fetch supported converters
  const { data: supportedConverters } = useQuery({
    queryKey: ['supportedConverters'],
    queryFn: async () => {
      const response = await converterApi.getSupportedConverters()
      return response.data
    },
  })

  // Fetch supported clocks
  const { data: supportedClocks } = useQuery({
    queryKey: ['supportedClocks'],
    queryFn: async () => {
      const response = await clockApi.getSupportedClocks()
      return response.data
    },
  })

  // Fetch FPGA dev kits
  const { data: fpgaDevKits } = useQuery({
    queryKey: ['fpgaDevKits'],
    queryFn: async () => {
      const response = await systemApi.getFPGADevKits()
      return response.data
    },
  })

  // Fetch FPGA constraints
  const { data: fpgaConstraints } = useQuery({
    queryKey: ['fpgaConstraints'],
    queryFn: async () => {
      const response = await systemApi.getFPGAConstraints()
      return response.data
    },
  })

  // Fetch quick modes when converter is selected
  useEffect(() => {
    if (converterPart) {
      converterApi.getQuickModes(converterPart).then((res) => {
        setQuickModes(res.data)
        // Set defaults
        if (res.data) {
          const firstClass = Object.keys(res.data)[0]
          setJesdClass(firstClass)
          const firstMode = Object.keys(res.data[firstClass])[0]
          setQuickMode(firstMode)
        }
      })
    }
  }, [converterPart])

  // Set default output clock selections
  useEffect(() => {
    if (fpgaConstraints?.out_clk_selections) {
      setOutClkSelect(fpgaConstraints.out_clk_selections)
    }
  }, [fpgaConstraints])

  // Solve system configuration
  const solveMutation = useMutation({
    mutationFn: async () => {
      const config = {
        converter_part: converterPart,
        clock_part: clockPart,
        fpga_dev_kit: fpgaDevKit,
        reference_rate: referenceRate,
        sample_clock: sampleClock,
        decimation: decimation,
        quick_mode: quickMode,
        jesd_class: jesdClass,
        ref_clock_constraint: refClockConstraint,
        sys_clk_select: sysClkSelect,
        out_clk_select: outClkSelect,
        force_pll: forcePll,
      }
      const response = await systemApi.solveConfig(config)
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
      converter_part: converterPart,
      clock_part: clockPart,
      fpga_dev_kit: fpgaDevKit,
      reference_rate: referenceRate,
      sample_clock: sampleClock,
      decimation: decimation,
      quick_mode: quickMode,
      jesd_class: jesdClass,
      ref_clock_constraint: refClockConstraint,
      sys_clk_select: sysClkSelect,
      out_clk_select: outClkSelect,
      force_pll: forcePll,
    }

    try {
      const response = await systemApi.getDiagram(config)
      const url = URL.createObjectURL(response.data)
      setDiagramUrl(url)
    } catch (error) {
      console.error('Failed to fetch diagram:', error)
    }
  }

  const forcePllOptions = ['Auto', 'Force QPLL', 'Force QPLL1', 'Force CPLL']

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        System Configurator
      </Typography>

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">System Settings</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Converter Part</InputLabel>
                <Select
                  value={converterPart}
                  label="Converter Part"
                  onChange={(e) => setConverterPart(e.target.value)}
                >
                  {supportedConverters?.map((part) => (
                    <MenuItem key={part} value={part}>
                      {part.toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Clock Part</InputLabel>
                <Select
                  value={clockPart}
                  label="Clock Part"
                  onChange={(e) => setClockPart(e.target.value)}
                >
                  {supportedClocks?.map((part) => (
                    <MenuItem key={part} value={part}>
                      {part.toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>FPGA Development Kit</InputLabel>
                <Select
                  value={fpgaDevKit}
                  label="FPGA Development Kit"
                  onChange={(e) => setFpgaDevKit(e.target.value)}
                >
                  {fpgaDevKits?.map((kit) => (
                    <MenuItem key={kit} value={kit}>
                      {kit.toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Reference Rate (VCXO) (Hz)"
                value={referenceRate}
                onChange={(e) => setReferenceRate(Number(e.target.value))}
                inputProps={{
                  min: 100e6,
                  max: 400e6,
                }}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Grid container spacing={2} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Converter Configuration
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Sample Clock (Hz)"
                  value={sampleClock}
                  onChange={(e) => setSampleClock(Number(e.target.value))}
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Decimation"
                  value={decimation}
                  onChange={(e) => setDecimation(Number(e.target.value))}
                  inputProps={{ min: 1 }}
                />
              </Grid>

              {quickModes && (
                <>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>JESD Class</InputLabel>
                      <Select
                        value={jesdClass}
                        label="JESD Class"
                        onChange={(e) => {
                          setJesdClass(e.target.value)
                          const firstMode = Object.keys(quickModes[e.target.value])[0]
                          setQuickMode(firstMode)
                        }}
                      >
                        {Object.keys(quickModes).map((cls) => (
                          <MenuItem key={cls} value={cls}>
                            {cls.toUpperCase()}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Quick Configuration Mode</InputLabel>
                      <Select
                        value={quickMode}
                        label="Quick Configuration Mode"
                        onChange={(e) => setQuickMode(e.target.value)}
                      >
                        {jesdClass &&
                          Object.entries(quickModes[jesdClass] || {}).map(
                            ([mode, settings]: [string, any]) => (
                              <MenuItem key={mode} value={mode}>
                                {jesdClass.toUpperCase()} Mode: {mode} (M={settings.M}, F=
                                {settings.F}, K={settings.K}, L={settings.L})
                              </MenuItem>
                            )
                          )}
                      </Select>
                    </FormControl>
                  </Grid>
                </>
              )}
            </Grid>
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              FPGA Configuration
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>FPGA Reference Clock Constraint</InputLabel>
                  <Select
                    value={refClockConstraint}
                    label="FPGA Reference Clock Constraint"
                    onChange={(e) => setRefClockConstraint(e.target.value)}
                  >
                    {fpgaConstraints?.ref_clock_constraints?.map((constraint: string) => (
                      <MenuItem key={constraint} value={constraint}>
                        {constraint}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>XCVR System Clock Source Selection</InputLabel>
                  <Select
                    value={sysClkSelect}
                    label="XCVR System Clock Source Selection"
                    onChange={(e) => setSysClkSelect(e.target.value)}
                  >
                    {fpgaConstraints?.sys_clk_selections?.map((selection: string) => (
                      <MenuItem key={selection} value={selection}>
                        {selection}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>XCVR Output Clock Selection</InputLabel>
                  <Select
                    multiple
                    value={outClkSelect}
                    label="XCVR Output Clock Selection"
                    onChange={(e) => setOutClkSelect(e.target.value as string[])}
                  >
                    {fpgaConstraints?.out_clk_selections?.map((selection: string) => (
                      <MenuItem key={selection} value={selection}>
                        {selection}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Transceiver PLL Selection</InputLabel>
                  <Select
                    value={forcePll}
                    label="Transceiver PLL Selection"
                    onChange={(e) => setForcePll(e.target.value)}
                  >
                    {forcePllOptions.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, mb: 3 }}>
        <Button
          variant="contained"
          size="large"
          onClick={() => solveMutation.mutate()}
          disabled={
            !converterPart ||
            !clockPart ||
            !fpgaDevKit ||
            !quickMode ||
            solveMutation.isPending
          }
        >
          {solveMutation.isPending ? 'Solving...' : 'Solve System Configuration'}
        </Button>
      </Box>

      {solution && (
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Solution</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {solution.success ? (
              <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                <pre style={{ overflow: 'auto' }}>
                  {JSON.stringify(solution.config, null, 2)}
                </pre>
              </Paper>
            ) : (
              <Alert severity="error">
                Failed to solve system configuration: {solution.error}
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
              alt="System Diagram"
              sx={{ width: '100%', height: 'auto' }}
            />
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  )
}
