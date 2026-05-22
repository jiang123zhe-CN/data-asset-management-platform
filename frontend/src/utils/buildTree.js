export default function buildTree(flatList, parentId = null) {
  return flatList
    .filter((item) => item.parent_id === parentId)
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((item) => ({
      key: item.id,
      title: item.name,
      data: item,
      children: buildTree(flatList, item.id),
    }))
}
