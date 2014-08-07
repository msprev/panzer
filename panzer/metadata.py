# Functions for manipulating metadata

def update_metadata(old, new):
    """ return old updated with new metadata """
    # 1. Update with values in 'metadata' field
    try:
        old.update(get_content(new, 'metadata', 'MetaMap'))
        del new['metadata']
    except (PanzerKeyError, KeyError):
        pass
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
    # 2. Update with values in fields for additive lists
    for field in ADDITIVE_FIELDS:
        try:
            try:
                new_list = get_content(new, field, 'MetaList')
            except PanzerKeyError:
                # field not in incoming metadata, move to next list
                continue
            try:
                old_list = get_content(old, field, 'MetaList')
            except PanzerKeyError:
                # field not in old metadata, start with an empty list
                old_list = []
        except PanzerTypeError as error:
            # wrong type of value under field, skip to next list
            log('WARNING', 'panzer', error)
            continue
        old_list.extend(new_list)
        set_content(old, field, old_list, 'MetaList')
        del new[field]
    # 3. Update with values of all remaining fields
    # - includes 'template' field
    old.update(new)
    return old

def apply_kill_rules(old_list):
    """ return old_list after applying kill rules """
    new_list = []
    for item in old_list:
        # 1. Sanity checks
        check_c_and_t_exist(item)
        item_content = item[C]
        item_type = item[T]
        if item_type != 'MetaMap':
            log('ERROR',
                'panzer',
                'fields "' + '", "'.join(ADDITIVE_FIELDS) + '" '
                'value must be of type "MetaMap"---ignoring 1 item')
            continue
        if len(item_content.keys() & {'run', 'kill', 'killall'}) != 1:
            log('ERROR',
                'panzer',
                'must contain exactly one "run", "kill", or "killall" per item'
                '---ignoring 1 item')
            continue
        # 2. Now operate on content
        if 'run' in item_content:
            if get_type(item_content, 'run') != 'MetaInlines':
                log('ERROR',
                    'panzer',
                    '"run" value must be of type "MetaInlines"'
                    '---ignoring 1 item')
                continue
            new_list.append(item)
        elif 'kill' in item_content:
            try:
                to_be_killed = get_content(item_content, 'kill', 'MetaInlines')
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
            new_list = [new_item for new_item in new_list if
                        get_content(new_item[C], 'run', 'MetaInlines') !=
                        to_be_killed]
        elif 'killall' in item_content:
            try:
                if get_content(item_content, 'killall', 'MetaBool') == True:
                    new_list = []
            except PanzerTypeError as error:
                log('WARNING', 'panzer', error)
                continue
        else:
            # Should never occur, caught by previous syntax check
            continue
    return new_list

def get_nested_content(metadata, fields, expected_type_of_leaf=None):
    """ return content of field by traversing a list of MetaMaps

    args:
        metadata : dictionary to traverse
        fields       : list of fields to traverse in dictionary from
        shallowest to deepest. Content of every field, except the last,
        must be type 'MetaMap' (otherwise fields could not be traversed).
        The content of final field in the list is returned.
        expected_type_of_leaf : (optional) expected type of final field's
        content

    Returns:
        content of final field in list, or the empty dict ({}) if field of
        expected type is not found
    """
    current_field = fields.pop(0)
    try:
        # If on a branch...
        if fields:
            next_content = get_content(metadata, current_field, 'MetaMap')
            return get_nested_content(next_content,
                                      fields,
                                      expected_type_of_leaf)
        # Else on a leaf...
        else:
            return get_content(metadata, current_field, expected_type_of_leaf)
    except PanzerKeyError:
        # current_field not found, return {}: nothing to update
        return {}
    except PanzerTypeError as error:
        log('WARNING', 'panzer', error)
        # wrong type found, return {}: nothing to update
        return {}

def get_content(metadata, field, expected_type=None):
    """ return content of field """
    if field not in metadata:
        raise PanzerKeyError('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    if expected_type:
        found_type = metadata[field][T]
        if found_type != expected_type:
            raise PanzerTypeError('value of "%s": expecting type "%s", '
                                  'but found type "%s"'
                                  % (field, expected_type, found_type))
    return metadata[field][C]

def get_type(metadata, field):
    """ return type of field """
    if field not in metadata:
        raise PanzerKeyError('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    return metadata[field][T]

def set_content(metadata, field, content, content_type):
    """ set content and type of field in metadata """
    metadata[field] = {C: content, T: content_type}

def get_list_or_inline(metadata, field):
    """ return content of MetaList or MetaInlines item as a list """
    field_type = get_type(metadata, field)
    if field_type == 'MetaInlines':
        content_raw = get_content(metadata, field, 'MetaInlines')
        content = [ pandocfilters.stringify(content_raw) ]
        return content
    elif field_type == 'MetaList':
        content = []
        for content_raw in get_content(metadata, field, 'MetaList'):
            content.append(pandocfilters.stringify(content_raw))
        return content
    else:
        raise PanzerTypeError('"%s" value must be of type "MetaInlines" or "MetaList"'
                              % field)

def get_metadata(ast):
    """ returns metadata branch of ast or {} if not present """
    try:
        metadata = ast[0]['unMeta']
    except KeyError:
        metadata = {}
    return metadata

def check_c_and_t_exist(item):
    """ check item contains both C and T fields """
    if C not in item:
        message = 'Value of "%s" corrupt: "C" field missing' % repr(item)
        raise PanzerBadASTError(message)
    if T not in item:
        message = 'Value of "%s" corrupt: "T" field missing' % repr(item)
        raise PanzerBadASTError(message)

def make_json_message(document, run_lists, options):
    """ return json message to pass to executables """
    data = [{'metadata' : document.get_metadata(),
             'styledef' : document.styledef,
             'template' : document.template,
             'style' : document.style,
             'run_lists' : run_lists,
             'cli_options' : options}]
    json_message = json.dumps(data)
    return json_message
