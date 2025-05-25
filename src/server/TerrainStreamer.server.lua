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