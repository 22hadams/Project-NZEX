-- SETTINGS MODULE (ReplicatedStorage/Modules/SettingsModule.lua)
local Settings = {}

Settings.WorldSizeKm = 150 -- Entire terrain in km
Settings.ChunkPixelSize = 256 -- Each chunk is 256x256 pixels
Settings.RenderDistance = 2 -- Radius of chunks to load
Settings.VoxelSize = Vector3.new(4, 4, 4) -- Size of each voxel block
Settings.HeightMultiplier = 512 -- Max height scaling

return Settings


-- HEIGHTMAP DATA MODULE (ReplicatedStorage/Modules/HeightmapData/HeightmapData.lua)
local HeightmapData = {}
local ChunksFolder = script:WaitForChild("Chunks")

function HeightmapData:GetChunk(x, z)
    local name = "Chunk_" .. x .. "_" .. z
    local module = ChunksFolder:FindFirstChild(name)
    if module then
        return require(module)
    else
        warn("Missing chunk: ", name)
        return nil
    end
end

return HeightmapData


-- CHUNK MANAGER (ReplicatedStorage/Modules/ChunkManager.lua)
local ChunkManager = {}

local loadedChunks = {}

function ChunkManager:GetKey(x, z)
    return tostring(x) .. ":" .. tostring(z)
end

function ChunkManager:IsChunkLoaded(x, z)
    return loadedChunks[self:GetKey(x, z)] ~= nil
end

function ChunkManager:MarkLoaded(x, z)
    loadedChunks[self:GetKey(x, z)] = true
end

function ChunkManager:Unload(x, z)
    local key = self:GetKey(x, z)
    loadedChunks[key] = nil
end

function ChunkManager:GetLoadedChunks()
    return loadedChunks
end

return ChunkManager


-- TERRAIN STREAMER (ServerScriptService/TerrainStreamer.lua)
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local Terrain = workspace.Terrain

local Settings = require(ReplicatedStorage.Modules.SettingsModule)
local Heightmap = require(ReplicatedStorage.Modules.HeightmapData.HeightmapData)
local ChunkManager = require(ReplicatedStorage.Modules.ChunkManager)

local ChunkSize = Settings.ChunkPixelSize
local VoxelSize = Settings.VoxelSize
local HeightMultiplier = Settings.HeightMultiplier
local RenderDistance = Settings.RenderDistance

local function getPlayerChunkPosition(position)
    local x = math.floor(position.X / (ChunkSize * VoxelSize.X))
    local z = math.floor(position.Z / (ChunkSize * VoxelSize.Z))
    return x, z
end

local function generateChunk(cx, cz)
    if ChunkManager:IsChunkLoaded(cx, cz) then return end

    local chunk = Heightmap:GetChunk(cx, cz)
    if not chunk then return end

    for y = 1, #chunk do
        for x = 1, #chunk[1] do
            local height = chunk[y][x] / 255 -- normalize
            if height > 0 then
                local wx = (cx * ChunkSize + (x - 1)) * VoxelSize.X
                local wz = (cz * ChunkSize + (y - 1)) * VoxelSize.Z
                local wy = height * HeightMultiplier

                local regionSize = Vector3.new(VoxelSize.X, wy, VoxelSize.Z)
                local cf = CFrame.new(wx, wy / 2, wz)
                Terrain:FillBlock(cf, regionSize, Enum.Material.Grass)
            end
        end
    end

    ChunkManager:MarkLoaded(cx, cz)
end

Players.PlayerAdded:Connect(function(player)
    player.CharacterAdded:Connect(function(char)
        local hrp = char:WaitForChild("HumanoidRootPart")

        RunService.Heartbeat:Connect(function()
            local cx, cz = getPlayerChunkPosition(hrp.Position)
            for dx = -RenderDistance, RenderDistance do
                for dz = -RenderDistance, RenderDistance do
                    generateChunk(cx + dx, cz + dz)
                end
            end
        end)
    end)
end)
