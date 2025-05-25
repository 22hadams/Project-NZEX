local Settings = {}

Settings.WorldSizeKm = 150 -- Entire terrain in km
Settings.ChunkPixelSize = 256 -- Each chunk is 256x256 pixels
Settings.RenderDistance = 2 -- Radius of chunks to load
Settings.VoxelSize = Vector3.new(4, 4, 4) -- Size of each voxel block
Settings.HeightMultiplier = 512 -- Max height scaling

return Settings
