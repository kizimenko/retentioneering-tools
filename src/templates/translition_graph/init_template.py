init_code = """
    initialize({{
    serverId: '{server_id}',
    env: '{env}',
    configNodes: {nodes},
    configLinks: {links},
    nodesColsNames: {node_cols_names},
    linksWeightsNames: {links_weights_names},
    nodesThreshold: {nodes_threshold},
    linksThreshold: {links_threshold},
    showWeights: {show_weights},
    showPercents: {show_percents},
    showNodesNames: {show_nodes_names},
    showAllEdgesForTargets: {show_all_edges_for_targets},
    showNodesWithoutLinks: {show_nodes_without_links},
    useLayoutDump: Boolean({layout_dump}),
    weightTemplate: {weight_template}
}})
"""
