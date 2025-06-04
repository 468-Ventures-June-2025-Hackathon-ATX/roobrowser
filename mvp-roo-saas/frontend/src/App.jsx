import { useState, useEffect } from 'react'
import {
  ChakraProvider,
  Box,
  VStack,
  HStack,
  Heading,
  Button,
  Card,
  CardBody,
  Text,
  Badge,
  Link,
  Container,
  useToast,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
  Icon
} from '@chakra-ui/react'
import { ExternalLinkIcon, AddIcon, DeleteIcon } from '@chakra-ui/icons'

const API_BASE = '/api'

function App() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const toast = useToast()

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/projects`)
      if (!response.ok) throw new Error('Failed to fetch projects')
      const data = await response.json()
      setProjects(data)
    } catch (error) {
      toast({
        title: 'Error fetching projects',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setLoading(false)
    }
  }

  const createProject = async () => {
    try {
      setCreating(true)
      const response = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      })

      if (!response.ok) throw new Error('Failed to create project')

      const newProject = await response.json()

      toast({
        title: 'Project created!',
        description: `Workspace ${newProject.namespace} is being created`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      })

      // Refresh the project list
      fetchProjects()
    } catch (error) {
      toast({
        title: 'Error creating project',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setCreating(false)
    }
  }

  const deleteProject = async (namespace) => {
    try {
      const response = await fetch(`${API_BASE}/projects/${namespace}`, {
        method: 'DELETE',
      })

      if (!response.ok) throw new Error('Failed to delete project')

      toast({
        title: 'Project deleted',
        description: `Workspace ${namespace} has been deleted`,
        status: 'info',
        duration: 3000,
        isClosable: true,
      })

      // Refresh the project list
      fetchProjects()
    } catch (error) {
      toast({
        title: 'Error deleting project',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      })
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'ready': return 'green'
      case 'starting': return 'yellow'
      case 'creating': return 'blue'
      case 'pending': return 'orange'
      default: return 'gray'
    }
  }

  useEffect(() => {
    fetchProjects()
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchProjects, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <ChakraProvider>
      <Container maxW="container.lg" py={8}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <Box textAlign="center">
            <Heading size="xl" mb={2}>
              🦘 Roo SaaS MVP
            </Heading>
            <Text color="gray.600" fontSize="lg">
              On-demand VSCode workspaces with Roo Code
            </Text>
          </Box>

          {/* Create Project Section */}
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <Heading size="md">Create New Workspace</Heading>
                <Text color="gray.600" textAlign="center">
                  Click the button below to spin up a new VSCode workspace with Roo Code pre-installed
                </Text>
                <Button
                  leftIcon={<AddIcon />}
                  colorScheme="blue"
                  size="lg"
                  onClick={createProject}
                  isLoading={creating}
                  loadingText="Creating..."
                >
                  Create Project
                </Button>
              </VStack>
            </CardBody>
          </Card>

          <Divider />

          {/* Projects List */}
          <Box>
            <HStack justify="space-between" mb={4}>
              <Heading size="md">Active Workspaces</Heading>
              <Button
                size="sm"
                variant="outline"
                onClick={fetchProjects}
                isLoading={loading}
              >
                Refresh
              </Button>
            </HStack>

            {loading && projects.length === 0 ? (
              <Box textAlign="center" py={8}>
                <Spinner size="lg" />
                <Text mt={4} color="gray.600">Loading workspaces...</Text>
              </Box>
            ) : projects.length === 0 ? (
              <Alert status="info">
                <AlertIcon />
                <Box>
                  <AlertTitle>No active workspaces</AlertTitle>
                  <AlertDescription>
                    Create your first workspace using the button above!
                  </AlertDescription>
                </Box>
              </Alert>
            ) : (
              <VStack spacing={4} align="stretch">
                {projects.map((project) => (
                  <Card key={project.namespace}>
                    <CardBody>
                      <HStack justify="space-between" align="center">
                        <VStack align="start" spacing={1}>
                          <HStack>
                            <Text fontWeight="bold">{project.namespace}</Text>
                            <Badge colorScheme={getStatusColor(project.status)}>
                              {project.status}
                            </Badge>
                          </HStack>
                          <Text fontSize="sm" color="gray.600">
                            {project.url}
                          </Text>
                        </VStack>

                        <HStack spacing={2}>
                          {project.status === 'ready' ? (
                            <Link href={project.url} isExternal>
                              <Button
                                leftIcon={<ExternalLinkIcon />}
                                colorScheme="green"
                                size="sm"
                              >
                                Open IDE
                              </Button>
                            </Link>
                          ) : (
                            <Button
                              leftIcon={<Spinner size="xs" />}
                              colorScheme="blue"
                              size="sm"
                              isDisabled
                            >
                              Starting...
                            </Button>
                          )}

                          <Button
                            leftIcon={<DeleteIcon />}
                            colorScheme="red"
                            variant="outline"
                            size="sm"
                            onClick={() => deleteProject(project.namespace)}
                          >
                            Delete
                          </Button>
                        </HStack>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            )}
          </Box>

          {/* Footer */}
          <Box textAlign="center" pt={8}>
            <Text fontSize="sm" color="gray.500">
              💡 Workspaces are automatically deleted after 2 hours
            </Text>
          </Box>
        </VStack>
      </Container>
    </ChakraProvider>
  )
}

export default App
