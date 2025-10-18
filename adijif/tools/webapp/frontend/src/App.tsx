import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import {
  Box,
  Container,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  AppBar,
  Toolbar,
  Typography,
} from '@mui/material'
import JESDModeSelector from './pages/JESDModeSelector'
import ClockConfigurator from './pages/ClockConfigurator'
import SystemConfigurator from './pages/SystemConfigurator'
import DropdownTest from './pages/DropdownTest'

const drawerWidth = 240

const pages = [
  { name: 'JESD204 Mode Selector', path: '/jesd-mode-selector', component: JESDModeSelector },
  { name: 'Clock Configurator', path: '/clock-configurator', component: ClockConfigurator },
  { name: 'System Configurator', path: '/system-configurator', component: SystemConfigurator },
  { name: 'Dropdown Test', path: '/dropdown-test', component: DropdownTest },
]

function App() {
  const [currentPage, setCurrentPage] = useState(0)

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Box
            component="img"
            src="/PyADI-JIF_logo.png"
            alt="PyADI-JIF Logo"
            sx={{ height: 40, mr: 2 }}
          />
          <Typography variant="h6" noWrap component="div">
            PyADI-JIF Tools Explorer
          </Typography>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', mt: 2 }}>
          <List>
            {pages.map((page, index) => (
              <ListItem key={page.name} disablePadding>
                <ListItemButton
                  selected={currentPage === index}
                  onClick={() => setCurrentPage(index)}
                  component="a"
                  href={page.path}
                >
                  <ListItemText primary={page.name} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Container maxWidth="xl">
          <Routes>
            <Route path="/" element={<Navigate to="/jesd-mode-selector" replace />} />
            {pages.map((page) => (
              <Route key={page.path} path={page.path} element={<page.component />} />
            ))}
          </Routes>
        </Container>
      </Box>
    </Box>
  )
}

export default App
