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
