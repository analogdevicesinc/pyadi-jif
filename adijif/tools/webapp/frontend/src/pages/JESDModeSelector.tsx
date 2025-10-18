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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Chip,
  FormGroup,
  FormControlLabel,
  Switch,
} from '@mui/material'
import { ExpandMore as ExpandMoreIcon, Help as HelpIcon } from '@mui/icons-material'
import { useQuery, useMutation } from '@tanstack/react-query'
import { converterApi } from '../api/client'

export default function JESDModeSelector() {
  const [selectedPart, setSelectedPart] = useState('')
  const [converterRate, setConverterRate] = useState(1)
  const [units, setUnits] = useState('GHz')
  const [decimation, setDecimation] = useState(1)
  const [cddcDecimation, setCDDCDecimation] = useState(1)
  const [fddcDecimation, setFDDCDecimation] = useState(1)
  const [cducInterpolation, setCDUCInterpolation] = useState(1)
  const [fducInterpolation, setFDUCInterpolation] = useState(1)
  const [helpOpen, setHelpOpen] = useState(false)
  const [converterInfo, setConverterInfo] = useState<any>(null)
  const [jesdControls, setJesdControls] = useState<any>(null)
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any[]>>({})
  const [validModes, setValidModes] = useState<any[]>([])
  const [showOnlyValid, setShowOnlyValid] = useState(true)

  // Fetch supported converters
  const { data: supportedParts } = useQuery({
    queryKey: ['supportedConverters'],
    queryFn: async () => {
      const response = await converterApi.getSupportedConverters()
      return response.data
    },
  })

  // Fetch converter info when part is selected
  useEffect(() => {
    if (selectedPart) {
      converterApi.getConverterInfo(selectedPart).then((res) => {
        setConverterInfo(res.data)
      })

      converterApi.getJESDControls(selectedPart).then((res) => {
        setJesdControls(res.data)
      })
    }
  }, [selectedPart])

  // Fetch valid modes when configuration changes
  const fetchModesMutation = useMutation({
    mutationFn: async () => {
      const scalarValue = units === 'Hz' ? 1 : units === 'kHz' ? 1e3 : units === 'MHz' ? 1e6 : 1e9
      const sampleClock = (converterRate * scalarValue) / decimation

      const config = {
        sample_clock: sampleClock,
        decimation: converterInfo?.converter_type === 'adc' ? decimation : undefined,
        interpolation: converterInfo?.converter_type === 'dac' ? decimation : undefined,
        cddc_decimation: cddcDecimation,
        fddc_decimation: fddcDecimation,
        cduc_interpolation: cducInterpolation,
        fduc_interpolation: fducInterpolation,
        filters: selectedFilters,
      }

      const response = await converterApi.getValidModes(selectedPart, config)
      return response.data
    },
    onSuccess: (data) => {
      setValidModes(data.modes || [])
    },
  })

  useEffect(() => {
    if (selectedPart && converterInfo) {
      fetchModesMutation.mutate()
    }
  }, [selectedPart, converterRate, units, decimation, cddcDecimation, fddcDecimation, cducInterpolation, fducInterpolation, selectedFilters])

  const handleFilterChange = (option: string, values: any[]) => {
    setSelectedFilters((prev) => ({
      ...prev,
      [option]: values,
    }))
  }

  const scalarValue = units === 'Hz' ? 1 : units === 'kHz' ? 1e3 : units === 'MHz' ? 1e6 : 1e9
  const sampleRate = (converterRate * scalarValue) / decimation / 1e6 // MSPS

  const filteredModes = showOnlyValid
    ? validModes.filter((mode) => mode.Valid === 'Yes')
    : validModes

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        JESD204 Mode Selector
      </Typography>

      <Button
        variant="outlined"
        startIcon={<HelpIcon />}
        onClick={() => setHelpOpen(true)}
        sx={{ mb: 2 }}
      >
        Help
      </Button>

      <Dialog open={helpOpen} onClose={() => setHelpOpen(false)} maxWidth="md">
        <DialogTitle>About JESD204 Mode Selector</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This tool helps you select the appropriate JESD204 mode for your application. It
            supports both ADCs, DACs, MxFEs, and Transceivers from the ADI portfolio. Modeling
            their JESD204 mode tables and clocking limitations of the individual devices.
            <br />
            <br />
            To use the tool, select a part from the dropdown menu. You can then configure the
            datapath settings such as decimation/interpolation and the converter sample rate. The
            tool will derive the necessary clocks for the selected configuration. Filter different
            JESD204 parameters to find a suitable mode for your application. The valid modes will be
            displayed in a table, along with the derived settings.
            <br />
            <br />
            JESD204 settings can be exported as CSV from the table.
          </DialogContentText>
        </DialogContent>
      </Dialog>

      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Select a Part</InputLabel>
        <Select
          value={selectedPart}
          label="Select a Part"
          onChange={(e) => setSelectedPart(e.target.value)}
        >
          {supportedParts?.map((part) => (
            <MenuItem key={part} value={part}>
              {part.toUpperCase()}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedPart && converterInfo && (
        <>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Datapath Configuration</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                {converterInfo.converter_type === 'adc' && (
                  <>
                    {converterInfo.cddc_decimations_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>CDDC Decimation</InputLabel>
                          <Select
                            value={cddcDecimation}
                            label="CDDC Decimation"
                            onChange={(e) => setCDDCDecimation(Number(e.target.value))}
                          >
                            {converterInfo.cddc_decimations_available.map((d: number) => (
                              <MenuItem key={d} value={d}>
                                {d}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                    {converterInfo.fddc_decimations_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>FDDC Decimation</InputLabel>
                          <Select
                            value={fddcDecimation}
                            label="FDDC Decimation"
                            onChange={(e) => setFDDCDecimation(Number(e.target.value))}
                          >
                            {converterInfo.fddc_decimations_available.map((d: number) => (
                              <MenuItem key={d} value={d}>
                                {d}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                    {converterInfo.decimation_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Decimation</InputLabel>
                          <Select
                            value={decimation}
                            label="Decimation"
                            onChange={(e) => setDecimation(Number(e.target.value))}
                          >
                            {converterInfo.decimation_available.map((d: number) => (
                              <MenuItem key={d} value={d}>
                                {d}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                  </>
                )}

                {converterInfo.converter_type === 'dac' && (
                  <>
                    {converterInfo.cduc_interpolations_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>CDUC Interpolation</InputLabel>
                          <Select
                            value={cducInterpolation}
                            label="CDUC Interpolation"
                            onChange={(e) => setCDUCInterpolation(Number(e.target.value))}
                          >
                            {converterInfo.cduc_interpolations_available.map((i: number) => (
                              <MenuItem key={i} value={i}>
                                {i}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                    {converterInfo.fduc_interpolations_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>FDUC Interpolation</InputLabel>
                          <Select
                            value={fducInterpolation}
                            label="FDUC Interpolation"
                            onChange={(e) => setFDUCInterpolation(Number(e.target.value))}
                          >
                            {converterInfo.fduc_interpolations_available.map((i: number) => (
                              <MenuItem key={i} value={i}>
                                {i}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                    {converterInfo.interpolation_available && (
                      <Grid item xs={12} md={6}>
                        <FormControl fullWidth>
                          <InputLabel>Interpolation</InputLabel>
                          <Select
                            value={decimation}
                            label="Interpolation"
                            onChange={(e) => setDecimation(Number(e.target.value))}
                          >
                            {converterInfo.interpolation_available.map((i: number) => (
                              <MenuItem key={i} value={i}>
                                {i}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                    )}
                  </>
                )}

                <Grid item xs={12} md={6}>
                  <FormControl fullWidth>
                    <InputLabel>Units</InputLabel>
                    <Select value={units} label="Units" onChange={(e) => setUnits(e.target.value)}>
                      <MenuItem value="Hz">Hz</MenuItem>
                      <MenuItem value="kHz">kHz</MenuItem>
                      <MenuItem value="MHz">MHz</MenuItem>
                      <MenuItem value="GHz">GHz</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label={`Converter Rate (${units})`}
                    value={converterRate}
                    onChange={(e) => setConverterRate(Number(e.target.value))}
                    inputProps={{
                      min: units === 'Hz' ? 1 : units === 'kHz' ? 100 : units === 'MHz' ? 1 : 0.1,
                      max: units === 'Hz' ? 28e9 : units === 'kHz' ? 28e6 : units === 'MHz' ? 28e3 : 28,
                      step: 0.1,
                    }}
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Sample Rate: {sampleRate.toFixed(2)} MSPS
                </Typography>
              </Box>
            </AccordionDetails>
          </Accordion>

          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Configuration
                </Typography>
                {jesdControls?.options &&
                  Object.entries(jesdControls.options).map(([option, values]: [string, any]) => (
                    <FormControl key={option} fullWidth sx={{ mb: 2 }}>
                      <InputLabel>{option}</InputLabel>
                      <Select
                        multiple
                        value={selectedFilters[option] || []}
                        label={option}
                        onChange={(e) => handleFilterChange(option, e.target.value as any[])}
                        renderValue={(selected) => (
                          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                            {(selected as any[]).map((value) => (
                              <Chip key={value} label={value} size="small" />
                            ))}
                          </Box>
                        )}
                      >
                        {values.map((value: any) => (
                          <MenuItem key={value} value={value}>
                            {value}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ))}
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">JESD204 Modes</Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showOnlyValid}
                        onChange={(e) => setShowOnlyValid(e.target.checked)}
                      />
                    }
                    label="Show only valid modes"
                  />
                </Box>

                <TableContainer sx={{ maxHeight: 600 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        {filteredModes.length > 0 &&
                          Object.keys(filteredModes[0]).map((key) => (
                            <TableCell key={key}>{key}</TableCell>
                          ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredModes.map((mode, idx) => (
                        <TableRow key={idx}>
                          {Object.values(mode).map((value: any, vidx) => (
                            <TableCell key={vidx}>{String(value)}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                {filteredModes.length === 0 && (
                  <Typography color="text.secondary">No modes found</Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  )
}
