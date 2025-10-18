import { useState } from 'react'
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Alert,
} from '@mui/material'

/**
 * Test page to verify Material-UI Select/Dropdown functionality
 * This uses static data to isolate frontend issues from API issues
 */
export default function DropdownTest() {
  const [selectedPart, setSelectedPart] = useState('')
  const [selectedUnit, setSelectedUnit] = useState('GHz')

  // Static test data - simulates what the API should return
  const testConverters = [
    'ad9680',
    'ad9144',
    'ad9081',
    'ad9371',
    'adrv9009',
  ]

  const units = ['Hz', 'kHz', 'MHz', 'GHz']

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Dropdown Functionality Test
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        This page uses static data to test that Material-UI Select components work correctly.
        If dropdowns work here but not on other pages, the issue is likely with API data loading.
      </Alert>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Test 1: Basic Dropdown
        </Typography>

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Select a Converter Part</InputLabel>
          <Select
            value={selectedPart}
            label="Select a Converter Part"
            onChange={(e) => setSelectedPart(e.target.value)}
          >
            {testConverters.map((part) => (
              <MenuItem key={part} value={part}>
                {part.toUpperCase()}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {selectedPart && (
          <Alert severity="success">
            Selected: <strong>{selectedPart.toUpperCase()}</strong>
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Test 2: Dropdown with Default Value
        </Typography>

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Select Units</InputLabel>
          <Select
            value={selectedUnit}
            label="Select Units"
            onChange={(e) => setSelectedUnit(e.target.value)}
          >
            {units.map((unit) => (
              <MenuItem key={unit} value={unit}>
                {unit}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Alert severity="info">
          Selected: <strong>{selectedUnit}</strong>
        </Alert>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Debugging Information
        </Typography>
        <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(
            {
              selectedPart,
              selectedUnit,
              converterCount: testConverters.length,
              unitCount: units.length,
            },
            null,
            2
          )}
        </Typography>
      </Paper>
    </Box>
  )
}
